import os
os.environ["LANGFUSE_DISABLED"] = "true"
os.environ["LANGFUSE_PUBLIC_KEY"] = "pk_..."
os.environ["LANGFUSE_SECRET_KEY"] = "sk_..."

from langfuse import Langfuse
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult


class LocalSpanExporter(SpanExporter):
    def __init__(self):
        self.spans = []

    def export(self, spans):
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


span_exporter = LocalSpanExporter()

langfuse = Langfuse(
    span_exporter=span_exporter,
)


def get_langfuse():
    return langfuse

def get_span_exporter():
    return span_exporter