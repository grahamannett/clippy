from clippy import logger


async def _use_tracing(self, ctx, use: bool = False):
    self._tracing_started = None
    if use:
        if not self._tracing_started:
            await ctx.tracing.start(screenshots=True, snapshots=True, sources=True)
            self._tracing_started = True
        else:
            await ctx.tracing.stop(path=f"{self._trace_dir}/trace.zip")


async def start_tracer(crawler: "Crawler"):
    logger.info("starting tracer...")
    await crawler.ctx.tracing.start(screenshots=True, snapshots=True, sources=True)


async def end_tracer(output_dir, crawler: "Crawler"):
    logger.info("ending tracer...")
    await crawler.ctx.tracing.stop(path=f"{output_dir}/trace.zip")


def parse_trace(trace_file):
    pass
