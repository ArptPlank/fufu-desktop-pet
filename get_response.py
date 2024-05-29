# -*- coding: utf-8 -*-
from transformers import AutoModelForCausalLM, AutoTokenizer,WhisperProcessor, WhisperForConditionalGeneration
from transformers import TextIteratorStreamer
from threading import Thread
from queue import Queue
import requests
from pydub import AudioSegment,silence
from pydub.playback import play
from io import BytesIO
from connect_Internt import search_keyword_and_collect_data,get_weather,get_location
from generate_image import generate_image
import warnings
import time
import os
import torch
import librosa
class Chat:
    def __init__(self):
        # 忽略特定类型的警告
        warnings.filterwarnings("ignore")
        self.device = "cuda"  # the device to load the model onto
        if not os.path.exists('cache'):
            os.mkdir('cache')
        if not os.path.exists('audio'):
            os.mkdir('audio')

        self.model = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen1.5-4B-Chat-GPTQ-Int4",  # the quantized model
            device_map="auto",
            cache_dir='./cache',
        )
        self.tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen1.5-4B-Chat-GPTQ-Int4", cache_dir='./cache')
        self.streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)
        # 读取人物设定
        with open("character_setting.txt", "r", encoding="utf-8") as f:
            self.character = f.read()
        location = get_location()
        weather = get_weather(location[:2])
        #初始化对话
        self.messages = [
            {
                "role": "system",
                "content":self.character},
            {
                "role": "system",
                "content":"我让你画画的时候不要说你不能画画，而是假设你能画画，然后仔细的描述这幅画的内容,绝对不能说你是AI，或者一个虚拟人物，你是一个真实的人物，你有自己的思维和感情，你可以回答任何问题，但是你不能说你不知道或者不会，你需要根据你的经验和知识来回答问题，你不知道的信息我会给你，但是绝对不能说你不会或者你不知道"
            },
            {
                "role": "user",
                "content": f"这是当前位置：{location}，这是未来几天的天气信息{weather}，今天的日期是{time.strftime('%Y-%m-%d', time.localtime())}"
            }
        ]

        #初始化语音识别模块
        self.processor = WhisperProcessor.from_pretrained("openai/whisper-small", cache_dir="cache")
        self.model_audio_to_text = WhisperForConditionalGeneration.from_pretrained("openai/whisper-small", cache_dir="cache").to(self.device)
        self.model_audio_to_text.config.forced_decoder_ids = None

        #使用队列来存储生成的文本
        self.response = Queue()
        self.image_path = None
        #获取显存大小小于16G的显卡不使用绘图
        memory_size = torch.cuda.get_device_properties(0).total_memory
        memory_size = memory_size / 1024 / 1024 / 1024
        memory_size = int(memory_size)
        print(f"显存大小{memory_size}G")
        user_input = input("是否启用绘图模块？(y/n),默认不启用：")
        if memory_size < 12:
            self.generate_image = None
        elif user_input == "n":
            self.generate_image = None
        elif user_input == "y":
            self.generate_image = generate_image()
        elif user_input == "":
            self.generate_image = None
        else:
            self.generate_image = generate_image()


    def generate(self, prompt, search_enabled=False,system=False):
        memory_size = torch.cuda.get_device_properties(0).total_memory
        memory_size = memory_size / 1024 / 1024 / 1024
        memory_size = int(memory_size)
        if memory_size < 3:
            #卸载绘画模块
            del self.generate_image
            torch.cuda.empty_cache()
            self.generate_image = None
        if "画一" in prompt and self.generate_image is None:
            self.response.put("显存不足或者您已禁用，无法绘图")
            return
        if "画一" in prompt:
            prompt = f"{prompt}，绝对不能说你不知道或者不会，假设你真的画过这幅画，你需要给出画面的描述，你可以根据你的经验和知识来描述这幅画"
        if system:
            self.messages.append({"role": "system", "content": prompt})
        else:
            self.messages.append({"role": "user", "content": prompt})
        if search_enabled:
            search_data = self.search()
            #print("search_data",search_data)
            self.messages[-1]["content"] = f"{prompt}，这是搜索到的你需要的信息{search_data}，请根据这些信息给出回答，绝对不能说你不知道或者不会，你需要根据这些信息给出回答"
        generated_text = self.generated_response(self.messages,stream=True)
        self.messages.append({"role": "assistant", "content": generated_text})
        if "画一" in prompt:
            self.response.put("content completed begin generate image")
        else:
            self.response.put("completed")

        if "画一" in prompt:
            t = Thread(target=self.get_image, args=(generated_text,))
            t.start()
        t = Thread(target=self.generate_audio, args=(generated_text,))
        t.start()

    def generate_audio(self,text):
        # 清除不常规字符
        text = text.replace('~', ',')
        # 转化为url编码
        text = requests.utils.quote(text)
        # 发送 Get 请求
        response = requests.get(f"http://127.0.0.1:5000/tts?character=fufu&text={text}")
        # 可以根据需要处理响应
        if response.status_code == 200:
            # 使用 BytesIO 从二进制数据创建音频段
            audio = AudioSegment.from_file(BytesIO(response.content), format="wav")
            # 使用 pydub 的 silence 模块找到音量非零的部分
            non_silent_chunks = silence.detect_nonsilent(
                audio,
                min_silence_len=4000,  # 检测100毫秒以上的静音
                silence_thresh=audio.dBFS - 20  # 静音阈值（小于平均音量16dBFS）
            )
            # 创建一个新的音频段，仅包含有声部分
            non_silent_audio = AudioSegment.empty()
            for start_i, end_i in non_silent_chunks:
                non_silent_audio += audio[start_i:end_i]

            # 播放处理后的音频
            play(non_silent_audio)
        else:
            print("请求失败，状态码:", response.status_code)

    def search(self):
        history = self.messages.copy()
        history.append({"role": "system", "content": "请给出你回答这个问题需要搜索的关键词"})
        response = self.generated_response(history)
        search_data = search_keyword_and_collect_data(response)
        #处理搜索结果
        search_data = [{"role": "system", "content": f"你是一个专门总结搜索到的信息的人，这些信息中有没有用的信息，你需要根据我给你的关键词来总结出有用的信息，这些信息是markdown格式的"},
                       {"role": "user", "content": f"这是关键词：{response}，这是搜索到的信息{search_data}，请给出总结的信息"}]
        # search_data = response
        search_data = self.generated_response(search_data)
        return search_data

    def get_image(self, prompt):
        memssages = [
            {"role": "system",
             "content": "你是一个画家，用户会给你一个描述，你需要根据这个描述写出一些提示词，提示词要用英文，提示词之间用英文逗号隔开"},
            {"role": "user",
             "content": f"这幅画的描述是{prompt}，请给出提示词"}
        ]
        response = self.generated_response(memssages)
        self.image_path = self.generate_image.generate_image(response)
        self.response.put("image completed")

    def generated_response(self,messages,stream=False):
        if stream:
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
            model_inputs = self.tokenizer([text], return_tensors="pt").to(self.device)

            generation_kwargs = dict(model_inputs, streamer=self.streamer, max_new_tokens=128)
            thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
            thread.start()
            generated_text = ""
            for new_text in self.streamer:
                generated_text += new_text
                self.response.put(new_text)
            #清理显存
            del model_inputs
            del generation_kwargs
            torch.cuda.empty_cache()
        else:
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
            model_inputs = self.tokenizer([text], return_tensors="pt").to(self.device)
            generated_ids = self.model.generate(
                model_inputs.input_ids,
                max_new_tokens=256
            )
            generated_ids = [
                output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
            ]
            generated_text = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
            #清理显存
            del model_inputs
            del generated_ids
            torch.cuda.empty_cache()

        return generated_text

    def audio_to_text(self,audio_path):
        audio_array, sr_original = librosa.load(audio_path, sr=None)
        if sr_original != 16000:
            audio_array = librosa.resample(audio_array, orig_sr=sr_original, target_sr=16000)
        input_features = self.processor(audio_array, sampling_rate=16000, return_tensors="pt").input_features.to(self.device)
        predicted_ids = self.model_audio_to_text.generate(input_features)
        transcription = self.processor.batch_decode(predicted_ids, skip_special_tokens=True)
        prompt = [{"role": "system", "content": "你是一个纠错员，用户说的文字有错误，你需要根据你的经验和知识来纠正这些错误，你需要给出纠正后的文字，绝对不能说你不知道或者不会，你需要根据你的经验和知识来纠正这些错误"}
                  , {"role": "user", "content": f"这是需要修改的文字：{transcription}，请给出纠正后的文字，不要简化语句，或者删除文字，也不要增加文字，你只需要把原来的文字的繁体字或者错别字纠正，并修改成简体字即可"}]
        response = self.generated_response(prompt)
        os.remove(audio_path)
        return response

    def reset_memory(self):
        del self.messages
        torch.cuda.empty_cache()
        self.messages = [
            {"role": "system",
             "content": self.character}
        ]
        self.response = Queue()


if __name__ == "__main__":
    chat = Chat()
    chat.generate("你好啊，你能简单的介绍一下自己吗？大概100个字")


