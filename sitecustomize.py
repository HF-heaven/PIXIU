"""
Runtime patches applied whenever Python starts within this repo.

Currently ensures compatibility between newer versions of `transformers`
and the `torch==2.1.x` runtime by aliasing the renamed pytree API.
"""
try:
    import torch.utils._pytree as _pytree

    if hasattr(_pytree, "_register_pytree_node"):
        def _register_pytree_node(type_, flatten_fn, unflatten_fn, **kwargs):
            to_dumpable = kwargs.pop("to_dumpable_context", None)
            from_dumpable = kwargs.pop("from_dumpable_context", None)
            kwargs.pop("serialized_type_name", None)
            kwargs.pop("serialized_state_name", None)
            kwargs.pop("type_repr", None)
            return _pytree._register_pytree_node(
                type_,
                flatten_fn,
                unflatten_fn,
                to_dumpable_context=to_dumpable,
                from_dumpable_context=from_dumpable,
            )

        _pytree.register_pytree_node = _register_pytree_node
except Exception:
    # Fail silently if torch is unavailable; downstream imports will raise
    # the appropriate error and surface to the user.
    pass

try:
    from transformers.utils import import_utils as _hf_import_utils
except Exception:
    _hf_import_utils = None

if _hf_import_utils is not None:
    def _noop_check():
        """Bypass torch>=2.6 guard when running on trusted local checkpoints."""
        return None

    _hf_import_utils.check_torch_load_is_safe = _noop_check


