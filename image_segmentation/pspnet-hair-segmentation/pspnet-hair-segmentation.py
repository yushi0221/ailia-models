import sys
import time
import argparse

import numpy as np
import cv2

import ailia
# import original modules
sys.path.append('../../util')
from webcamera_utils import preprocess_frame, get_capture  # noqa: E402
from image_utils import load_image  # noqa: E402
from model_utils import check_and_download_models  # noqa: E402


# ======================
# Parameters
# ======================
WEIGHT_PATH = 'pspnet-hair-segmentation.onnx'
MODEL_PATH = WEIGHT_PATH + '.prototxt'
REMOTE_PATH =\
    'https://storage.googleapis.com/ailia-models/pspnet-hair-segmentation/'

IMAGE_PATH = 'test.jpg'
SAVE_IMAGE_PATH = 'output.png'
IMAGE_HEIGHT = 512
IMAGE_WIDTH = 512


# ======================
# Arguemnt Parser Config
# ======================
parser = argparse.ArgumentParser(
    description='Real-time hair segmentation model'
)
parser.add_argument(
    '-i', '--input', metavar='IMAGE',
    default=IMAGE_PATH,
    help='The input image path.'
)
parser.add_argument(
    '-v', '--video', metavar='VIDEO',
    default=None,
    help='The input video path. ' +
         'If the VIDEO argument is set to 0, the webcam input will be used.'
)
parser.add_argument(
    '-s', '--savepath', metavar='SAVE_IMAGE_PATH',
    default=SAVE_IMAGE_PATH,
    help='Save path for the output image.'
)
parser.add_argument(
    '-b', '--benchmark',
    action='store_true',
    help='Running the inference on the same input 5 times ' +
         'to measure execution performance. (Cannot be used in video mode)'
)
args = parser.parse_args()


# ======================
# Utils
# ======================
def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def postprocess(src_img, preds_ailia):
    pred = sigmoid(preds_ailia)[0][0]
    mask = pred >= 0.5

    mask_n = np.zeros((IMAGE_HEIGHT, IMAGE_WIDTH, 3))
    mask_n[:, :, 0] = 255
    mask_n[:, :, 0] *= mask

    image_n = cv2.cvtColor(src_img, cv2.COLOR_RGB2BGR)

    # discard padded area
    h, w, _ = image_n.shape
    delta_h = h - IMAGE_HEIGHT
    delta_w = w - IMAGE_WIDTH

    top = delta_h // 2
    bottom = IMAGE_HEIGHT - (delta_h - top)
    left = delta_w // 2
    right = IMAGE_WIDTH - (delta_w - left)

    mask_n = mask_n[top:bottom, left:right, :]
    image_n = image_n * 0.5 + mask_n * 0.5
    return image_n


# ======================
# Main functions
# ======================
def recognize_from_image():
    # prepare input data
    input_data = load_image(
        args.input,
        (IMAGE_HEIGHT, IMAGE_WIDTH),
        normalize_type='ImageNet',
        gen_input_ailia=True
    )
    src_img = load_image(
        args.input,
        (IMAGE_HEIGHT, IMAGE_WIDTH),
        normalize_type='None'
    )

    # net initialize
    env_id = ailia.get_gpu_environment_id()
    print(f'env_id: {env_id}')
    net = ailia.Net(MODEL_PATH, WEIGHT_PATH, env_id=env_id)

    # inference
    print('Start inference...')
    if args.benchmark:
        print('BENCHMARK mode')
        for i in range(5):
            start = int(round(time.time() * 1000))
            preds_ailia = net.predict(input_data)
            end = int(round(time.time() * 1000))
            print(f'\tailia processing time {end - start} ms')
    else:
        preds_ailia = net.predict(input_data)

    # postprocessing
    res_img = postprocess(src_img, preds_ailia)
    cv2.imwrite(args.savepath, res_img)
    print('Script finished successfully.')


def recognize_from_video():
    # net initialize
    env_id = ailia.get_gpu_environment_id()
    print(f'env_id: {env_id}')
    net = ailia.Net(MODEL_PATH, WEIGHT_PATH, env_id=env_id)

    capture = get_capture(args.video)

    while(True):
        ret, frame = capture.read()
        if (cv2.waitKey(1) & 0xFF == ord('q')) or not ret:
            break

        src_img, input_data = preprocess_frame(
            frame,
            IMAGE_HEIGHT,
            IMAGE_WIDTH,
            normalize_type='ImageNet'
        )

        src_img = cv2.resize(src_img, (IMAGE_WIDTH, IMAGE_HEIGHT))
        src_img = cv2.cvtColor(src_img, cv2.COLOR_BGR2RGB)

        preds_ailia = net.predict(input_data)

        res_img = postprocess(src_img, preds_ailia)
        cv2.imshow('frame', res_img / 255.0)

    capture.release()
    cv2.destroyAllWindows()
    print('Script finished successfully.')


def main():
    # model files check and download
    check_and_download_models(WEIGHT_PATH, MODEL_PATH, REMOTE_PATH)

    if args.video is not None:
        # video mode
        recognize_from_video()
    else:
        # image mode
        recognize_from_image()


if __name__ == '__main__':
    main()
