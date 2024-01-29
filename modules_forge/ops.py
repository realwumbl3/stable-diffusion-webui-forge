import torch
import contextlib
from ldm_patched.modules import model_management


@contextlib.contextmanager
def use_patched_ops(operations):
    op_names = ['Linear', 'Conv2d', 'Conv3d', 'GroupNorm', 'LayerNorm']
    backups = {op_name: getattr(torch.nn, op_name) for op_name in op_names}

    try:
        for op_name in op_names:
            setattr(torch.nn, op_name, getattr(operations, op_name))

        yield

    finally:
        for op_name in op_names:
            setattr(torch.nn, op_name, backups[op_name])
    return


@contextlib.contextmanager
def automatic_memory_management():
    model_management.free_memory(
        memory_required=3 * 1024 * 1024 * 1024,
        device=model_management.get_torch_device()
    )

    module_list = []

    original_init = torch.nn.Module.__init__
    original_to = torch.nn.Module.to

    def patched_init(self, *args, **kwargs):
        module_list.append(self)
        return original_init(self, *args, **kwargs)

    def patched_to(self, *args, **kwargs):
        module_list.append(self)
        return original_to(self, *args, **kwargs)

    try:
        torch.nn.Module.__init__ = patched_init
        torch.nn.Module.to = patched_to
        yield
    finally:
        torch.nn.Module.__init__ = original_init
        torch.nn.Module.to = original_to

    count = 0
    for module in set(module_list):
        module_params = getattr(module, '_parameters', [])
        if len(module_params) > 0:
            module.cpu()
            count += 1

    print(f'Automatic Memory Management: {count} Modules.')
    model_management.soft_empty_cache()

    return