import os

import gradio as gr

MODEL_ID = 'black-forest-labs/FLUX.1-schnell'
MODEL_REVISION = '741f7c3ce8b383c54771c7003378a50191e9efe9'
ENABLED = os.getenv('ENABLE_GENERATION', '0') == '1'
ZERO_GPU = os.getenv('SPACES_ZERO_GPU', '').lower() in ('1', 'true')
PERSONAS = {
    'jonas': 'a fictional German man aged 30, short brown hair, neat stubble, dark navy casual shirt',
    'mia': 'a fictional German woman aged 30, shoulder-length brown hair, casual beige sweater',
}
POSES = {
    'front': 'looking directly into the camera, relaxed attentive expression, mouth closed',
    'listening': 'looking slightly to the side, attentive expression, mouth closed',
}
pipe = None


def health():
    return {
        'service': 'tiktok-creative-worker',
        'version': 'presenter-bootstrap-v1',
        'generation_enabled': ENABLED,
        'zero_gpu': ZERO_GPU,
        'model_loaded': pipe is not None,
        'model_access_configured': bool(os.getenv('HF_MODEL_TOKEN')),
        'model': MODEL_ID,
        'revision': MODEL_REVISION,
        'capabilities': ['health', 'fictional_presenter_portrait'] if pipe is not None else ['health'],
        'product_edit': False,
        'video_generation': False,
        'lip_sync': False,
        'commercial_asset_review_required': True,
    }


def validate_request(persona, pose, seed):
    if persona not in PERSONAS or pose not in POSES:
        raise gr.Error('Unknown fictional presenter or pose')
    if type(seed) not in (int, float) or not 0 <= seed <= 2147483647 or int(seed) != seed:
        raise gr.Error('Seed must be an integer between 0 and 2147483647')
    return int(seed)


if ENABLED:
    if not ZERO_GPU:
        raise RuntimeError('Generation requires ZeroGPU; CPU and dedicated paid GPU modes are blocked')
    if not os.getenv('HF_MODEL_TOKEN'):
        raise RuntimeError('HF_MODEL_TOKEN with accepted model access is required before enabling generation')
    import spaces
    import torch
    from diffusers import FluxPipeline

    pipe = FluxPipeline.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        token=os.environ['HF_MODEL_TOKEN'],
        torch_dtype=torch.bfloat16,
    ).to('cuda')

    @spaces.GPU(duration=60)
    def generate_gpu(persona, pose, seed):
        prompt = (
            'Realistic smartphone portrait of ' + PERSONAS[persona] + ', ' + POSES[pose] + '. '
            'Waist-up composition with the whole head and shoulders visible, hands outside the frame. '
            'Bright ordinary home kitchen, natural window light, authentic unpolished creator look. '
            'No product, no packaging, no text, no logos, no watermark. Vertical photograph.'
        )
        with torch.inference_mode():
            image = pipe(
                prompt=prompt,
                height=1024,
                width=576,
                num_inference_steps=4,
                guidance_scale=0.0,
                max_sequence_length=256,
                generator=torch.Generator('cpu').manual_seed(seed),
            ).images[0]
        return image, {
            'model': MODEL_ID,
            'revision': MODEL_REVISION,
            'seed': seed,
            'persona': persona,
            'pose': pose,
            'width': image.width,
            'height': image.height,
            'fictional_identity': True,
            'is_ai_generated': True,
            'quality_status': 'pending',
            'billing_status': 'unverified',
            'product_evidence': False,
        }


def generate_presenter(persona, pose, seed):
    seed = validate_request(persona, pose, seed)
    if pipe is None:
        raise gr.Error('Generation is disabled. Only the health endpoint is available.')
    try:
        return generate_gpu(persona, pose, seed)
    except Exception:
        raise gr.Error('Generation did not complete. Do not retry automatically; inspect quota and Space logs.') from None


def create_app():
    with gr.Blocks() as demo:
        gr.Markdown('# Private Creative Worker\nStage 1: health check and fictional presenter portraits only.')
        status = gr.JSON(label='Service status')
        gr.Button('Check health').click(health, outputs=status, api_name='health', queue=False)
        persona = gr.Dropdown(choices=list(PERSONAS), value='jonas', label='Fictional presenter')
        pose = gr.Dropdown(choices=list(POSES), value='front', label='Pose')
        seed = gr.Number(value=72, precision=0, label='Seed')
        image = gr.Image(type='pil', label='Unreviewed generated portrait')
        metadata = gr.JSON(label='Asset metadata')
        gr.Button('Generate one portrait', interactive=ENABLED).click(
            generate_presenter,
            inputs=[persona, pose, seed],
            outputs=[image, metadata],
            api_name='generate_presenter',
            concurrency_limit=1,
            concurrency_id='gpu',
        )
    return demo.queue(max_size=2, default_concurrency_limit=1)


if __name__ == '__main__':
    create_app().launch(show_error=False)
