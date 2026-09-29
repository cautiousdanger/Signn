"""Export SoftmaxClassifier weights to a tiny ONNX MatMul+Softmax graph."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def export_softmax_onnx(weights: np.ndarray, dest: Path) -> None:
    """weights shape: (n_features + 1, n_classes) with last row = bias."""
    try:
        from onnx import TensorProto, helper, numpy_helper, save_model
    except ImportError as err:
        raise RuntimeError("onnx package required for export") from err

    w = np.asarray(weights, dtype=np.float32)
    n_features_plus_bias, n_classes = w.shape
    n_features = n_features_plus_bias - 1
    w_body = w[:-1, :]  # (F, C)
    bias = w[-1, :]  # (C,)

    w_init = numpy_helper.from_array(w_body, name="W")
    b_init = numpy_helper.from_array(bias, name="B")

    nodes = [
        helper.make_node("MatMul", ["input", "W"], ["logits_raw"]),
        helper.make_node("Add", ["logits_raw", "B"], ["logits"]),
        helper.make_node("Softmax", ["logits"], ["probs"], axis=1),
    ]
    graph = helper.make_graph(
        nodes,
        "softmax_sign_clf",
        [
            helper.make_tensor_value_info(
                "input", TensorProto.FLOAT, [None, n_features]
            )
        ],
        [
            helper.make_tensor_value_info(
                "probs", TensorProto.FLOAT, [None, n_classes]
            )
        ],
        [w_init, b_init],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = 8
    dest.parent.mkdir(parents=True, exist_ok=True)
    save_model(model, str(dest))


def weights_from_bundle(bundle: dict[str, Any]) -> np.ndarray:
    return np.asarray(bundle["weights"], dtype=np.float32)
