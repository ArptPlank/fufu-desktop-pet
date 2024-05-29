import torch
from diffusers import StableDiffusionPipeline, TCDScheduler
import os
import time

class generate_image():
    def __init__(self):
        self.device = "cuda"
        base_model_id = "runwayml/stable-diffusion-v1-5"
        tcd_lora_id = "h1t/TCD-SD15-LoRA"
        self.pipe = StableDiffusionPipeline.from_pretrained(base_model_id, torch_dtype=torch.float16, variant="fp16",cache_dir="cache").to(self.device)
        self.pipe.scheduler = TCDScheduler.from_config(self.pipe.scheduler.config)
        self.pipe.load_lora_weights(tcd_lora_id)
        self.pipe.fuse_lora()
        #检测Image文件夹是否存在
        if not os.path.exists('Image'):
            os.mkdir('Image')

    def generate_image(self, prompt,image_path="Image"):
        image = self.pipe(
            prompt=prompt,
            num_inference_steps=4,
            guidance_scale=0,
            eta=0.3,
            generator=torch.Generator(device=self.device).manual_seed(42),
        ).images[0]
        # Save the image
        image_name = time.strftime("%Y%m%d%H%M%S", time.localtime())
        image.save(f"{image_path}/{image_name}.png")
        return f"{image_path}/{image_name}.png"

if __name__ == "__main__":
    generate_image = generate_image()
    generate_image.generate_image("river ,mountains")