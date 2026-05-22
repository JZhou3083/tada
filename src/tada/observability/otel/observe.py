import functools
import inspect

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode


def observe(
    name: str | None = None,
    *,
    attributes: dict | None = None,
    capture_io: bool = True,
):
    def decorator(fn):
        span_name = name or getattr(fn, "__name__", fn.__class__.__name__)

        def _set_common_attrs(span, args, kwargs):
            if attributes:
                for k, v in attributes.items():
                    span.set_attribute(k, v)
            if capture_io and span.is_recording():
                span.set_attribute("input.args", repr(args)[:4000])
                span.set_attribute("input.kwargs", repr(kwargs)[:4000])

        def _set_output(span, result):
            if capture_io and span.is_recording():
                span.set_attribute("output", repr(result)[:4000])

        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs):
                tracer = trace.get_tracer(fn.__module__)
                with tracer.start_as_current_span(span_name) as span:
                    _set_common_attrs(span, args, kwargs)
                    try:
                        result = await fn(*args, **kwargs)
                        _set_output(span, result)
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise

            return async_wrapper

        @functools.wraps(fn)
        def sync_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(fn.__module__)
            with tracer.start_as_current_span(span_name) as span:
                _set_common_attrs(span, args, kwargs)
                try:
                    result = fn(*args, **kwargs)
                    _set_output(span, result)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        return sync_wrapper

    return decorator
