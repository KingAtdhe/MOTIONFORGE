"""Real-ESRGAN anime 6B (x4) without torch: weights read from the .pth zip with a restricted unpickler,
network built as an ONNX graph, run with onnxruntime.  usage: esrgan.py weights.pth in.png out.png"""
import collections, io, pickle, sys, zipfile
import numpy as np
import onnx
from onnx import helper, TensorProto, numpy_helper
import onnxruntime as ort
from PIL import Image


def load_pth(path):
    zf = zipfile.ZipFile(path)
    root = zf.namelist()[0].split("/")[0]

    class Storage:
        def __init__(self, key, dtype):
            self.key, self.dtype = key, dtype

    def rebuild(storage, offset, size, stride, *rest):
        raw = np.frombuffer(zf.read(f"{root}/data/{storage.key}"), dtype=storage.dtype)
        n = int(np.prod(size)) if size else 1
        a = raw[offset:offset + n] if all(True for _ in [0]) else raw
        return np.lib.stride_tricks.as_strided(raw[offset:], shape=tuple(size), strides=tuple(s * raw.itemsize for s in stride)).copy()

    DT = {"FloatStorage": np.float32, "HalfStorage": np.float16}

    class U(pickle.Unpickler):
        def find_class(self, mod, name):
            if mod == "collections" and name == "OrderedDict":
                return collections.OrderedDict
            if mod == "torch._utils" and name == "_rebuild_tensor_v2":
                return rebuild
            if mod == "torch" and name in DT:
                return name
            raise pickle.UnpicklingError(f"blocked {mod}.{name}")

        def persistent_load(self, pid):
            _, kind, key, _, _ = pid
            return Storage(key, DT[kind])

    obj = U(io.BytesIO(zf.read(f"{root}/data.pkl"))).load()
    return obj.get("params_ema", obj.get("params", obj))


def build(W, nb=6):
    nodes, inits = [], []
    cnt = [0]

    def nm(p):
        cnt[0] += 1
        return f"{p}_{cnt[0]}"

    def conv(x, key, act=False):
        w, b = W[key + ".weight"].astype(np.float32), W[key + ".bias"].astype(np.float32)
        inits.append(numpy_helper.from_array(w, key + ".w")); inits.append(numpy_helper.from_array(b, key + ".b"))
        y = nm(key)
        nodes.append(helper.make_node("Conv", [x, key + ".w", key + ".b"], [y], pads=[1, 1, 1, 1], kernel_shape=[3, 3]))
        if act:
            z = nm("lr"); nodes.append(helper.make_node("LeakyRelu", [y], [z], alpha=0.2)); return z
        return y

    def cat(xs):
        y = nm("cat"); nodes.append(helper.make_node("Concat", xs, [y], axis=1)); return y

    def add(a, b):
        y = nm("add"); nodes.append(helper.make_node("Add", [a, b], [y])); return y

    def scale(a, s):
        k = nm("k"); inits.append(numpy_helper.from_array(np.array(s, np.float32), k))
        y = nm("mul"); nodes.append(helper.make_node("Mul", [a, k], [y])); return y

    def up(a):
        sc = nm("sc"); inits.append(numpy_helper.from_array(np.array([1, 1, 2, 2], np.float32), sc))
        y = nm("up"); nodes.append(helper.make_node("Resize", [a, "", sc], [y], mode="nearest")); return y

    def rdb(x, p):
        x1 = conv(x, p + ".conv1", True)
        x2 = conv(cat([x, x1]), p + ".conv2", True)
        x3 = conv(cat([x, x1, x2]), p + ".conv3", True)
        x4 = conv(cat([x, x1, x2, x3]), p + ".conv4", True)
        x5 = conv(cat([x, x1, x2, x3, x4]), p + ".conv5")
        return add(scale(x5, 0.2), x)

    f = conv("input", "conv_first")
    b = f
    for i in range(nb):
        o = rdb(rdb(rdb(b, f"body.{i}.rdb1"), f"body.{i}.rdb2"), f"body.{i}.rdb3")
        b = add(scale(o, 0.2), b)
    f = add(f, conv(b, "conv_body"))
    f = conv(up(f), "conv_up1", True)
    f = conv(up(f), "conv_up2", True)
    out = conv(conv(f, "conv_hr", True), "conv_last")
    nodes.append(helper.make_node("Identity", [out], ["output"]))
    g = helper.make_graph(nodes, "rrdb", [helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, 3, None, None])],
                          [helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 3, None, None])], inits)
    m = helper.make_model(g, opset_imports=[helper.make_opsetid("", 17)])
    m.ir_version = 8
    return m


if __name__ == "__main__":
    W = load_pth(sys.argv[1])
    nb = 1 + max(int(k.split(".")[1]) for k in W if k.startswith("body."))
    m = build(W, nb)
    sess = ort.InferenceSession(m.SerializeToString(), providers=["CPUExecutionProvider"])
    im = np.asarray(Image.open(sys.argv[2]).convert("RGB")).astype(np.float32) / 255
    y = sess.run(None, {"input": im.transpose(2, 0, 1)[None]})[0][0]
    Image.fromarray((np.clip(y.transpose(1, 2, 0), 0, 1) * 255 + 0.5).astype(np.uint8)).save(sys.argv[3])
    print("blocks", nb, "out", y.shape)
