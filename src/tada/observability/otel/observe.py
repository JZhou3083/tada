import functools

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode


def observe(
    name: str | None = None, *, attributes: dict | None = None, capture_io: bool = True
):
    def decorator(fn):
        span_name = name or fn.__name__

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(fn.__module__)
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for k, v in attributes.items():
                        span.set_attribute(k, v)
                if capture_io and span.is_recording():
                    span.set_attribute("input.args", repr(args)[:4000])
                    span.set_attribute("input.kwargs", repr(kwargs)[:4000])
                try:
                    result = fn(*args, **kwargs)
                    if capture_io and span.is_recording():
                        span.set_attribute("output", repr(result)[:4000])
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        return wrapper

    return decorator
