"""Explicit provider selection, including DLL and session fallback."""
import warnings
import onnxruntime as ort


def create_session(path, device='auto'):
    if device not in ('auto', 'cpu', 'cuda'):
        raise ValueError('device must be auto, cpu or cuda')
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 4
    opts.log_severity_level = 3
    if device != 'cpu':
        if 'CUDAExecutionProvider' in ort.get_available_providers():
            try:
                if hasattr(ort, 'preload_dlls'):
                    ort.preload_dlls()
                session = ort.InferenceSession(str(path), sess_options=opts,
                    providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
                if 'CUDAExecutionProvider' in session.get_providers():
                    return session, 'cuda'
            except Exception as exc:
                warnings.warn(f'CUDA初期化失敗、CPUへ切替: {exc}')
        if device == 'cuda':
            raise RuntimeError('CUDAを利用できません。doctorとCUDA/cuDNN DLLを確認してください。')
        warnings.warn('CUDAを利用できないためCPUで生成します。')
    return ort.InferenceSession(str(path), sess_options=opts,
        providers=['CPUExecutionProvider']), 'cpu'
