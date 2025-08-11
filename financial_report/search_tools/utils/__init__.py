from os import path, remove, rename


class PipeAble:
    _result = None

    def __init__(self, func, *preset_args, **preset_kwargs):
        self.func = func
        self.preset_args = preset_args
        self.preset_kwargs = preset_kwargs

    def __call__(self, *args, **kwargs):
        if args or kwargs:
            return PipeAble(self.func, *self.preset_args, *args, **{**self.preset_kwargs, **kwargs})
        return self.func(*self.preset_args, **self.preset_kwargs)

    def __rrshift__(self, other):
        value = other.value if isinstance(other, PipeableValue) else other
        result = self.func(value, *self.preset_args, **self.preset_kwargs)
        return PipeableValue(result)



class PipeableValue:
    def __init__(self, value):
        self.value = value

    def __rshift__(self, func):
        if isinstance(func, PipeAble):
            result = func.func(self.value, *func.preset_args, **func.preset_kwargs)
        elif callable(func):
            # 对普通函数和lambda进行自动包装
            result = func(self.value)
        else:
            raise TypeError(f"Cannot pipe to object of type {type(func)}")
        return PipeableValue(result)

    def __call__(self):
        return self.value

    def __or__(self, func):
        return func(self.value)

    def __repr__(self):
        return f"{self.value!r}"

    def valueOf(self):
        return self.value


def use_pipe(value):
    """开始链式调用的工厂方法，最后自动解包值"""
    if isinstance(value, PipeableValue):
        return value()
    elif isinstance(value, (int, float, str, dict, list)):
        return PipeableValue(value)
    else:
        raise TypeError(f"Unsupported value type: {type(value)}")


def read_file(*args):
    with open(path.join(*args), 'r', encoding='utf-8') as f:
        return f.read()


def fix_markdown_table_spacing(md: str) -> str:
    lines, fixed_lines = md.split('\n'), []
    for i, line in enumerate(lines):
        if line.strip().startswith('|'):
            pre = lines[i - 1].strip()
            if not pre.startswith('|') and line:
                fixed_lines.append('\n')
        fixed_lines.append(line)
    return '\n'.join(fixed_lines)



