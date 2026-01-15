import torchvision.models as models
from .densenetccnl import dnetccnl
from .unetnc import UnetGenerator


def get_model(name: str, n_classes: int, in_channels: int = 3):
    """
    name: 'unetnc' or 'dnetccnl'
    n_classes: infer.py에서 전달되는 출력 채널 수 (wc/bm 각각 다를 수 있음)
    in_channels: 입력 이미지 채널 수 (RGB=3)
    """
    name = (name or "").lower().strip()

    if name == "unetnc":
        # UNet: input_nc, output_nc, num_downs 필수
        # 128x128 기준 num_downs=7이 일반적
        return UnetGenerator(input_nc=in_channels, output_nc=n_classes, num_downs=7)

    if name == "dnetccnl":
        # DenseNet 기반 mapping network: out_channels가 flow(보통 2)
        return dnetccnl(img_size=128, in_channels=in_channels, out_channels=n_classes)

    print(f"Model {name} not available")
    return None



def _get_model_instance(name):
    try:
        return {
            'dnetccnl': dnetccnl,
            'unetnc': UnetGenerator,
        }[name]
    except:
        print('Model {} not available'.format(name))
