async def _use_tracing(self, ctx: BrowserContext, use: bool = False):
    self._tracing_started = None
    if use:
        if not self._tracing_started:
            await ctx.tracing.start(screenshots=True, snapshots=True, sources=True)
            self._tracing_started = True
        else:
            await ctx.tracing.stop(path=f"{self._trace_dir}/trace.zip")
