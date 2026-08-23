# TensorRT Experiments

TensorRT work is optional and version-gated by the driver, CUDA runtime, ONNX
opset, and target GPU. Never commit serialized engines; record model provenance,
conversion settings, accuracy change, latency, throughput, and target hardware.
