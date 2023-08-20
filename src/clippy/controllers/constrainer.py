import torch
import torch.nn as nn

class Constrainer(torch.nn.Module):
    def __init__(self, tokens: List[int]) -> None:
        super().__init__()
        self.latents = torch.nn.Parameter(torch.randn(config.num_latents, config.d_latents))

    def forward(self, text: str) -> torch.Tensor:
        pass


class ActionConstrainer(nn.Module):

    def __init__(self) -> None:
        super().__init__()

    def forward(self, x: torch.Tensor, type_: str) --> torch.Tensor:
        pass



from typing import Dict, List, Optional, Tuple
# https://github.com/google-research/google-research/blob/master/multi_game_dt/Multi_game_decision_transformers_public_colab.ipynb
def optimal_action(rng: torch.Tensor, # think this is equivalent to seed?
                    inputs: Dict[str, torch.Tensor],
                    logits_fn,
                    return_range: Tuple[int],
                    single_return_token: bool = False,
                    opt_weight: Optional[float] = 0.0,
                    num_samples: Optional[int] = 128,
                    action_temperature: Optional[float] = 1.0,
                    return_temperature: Optional[float] = 1.0,
                    action_top_percentile: Optional[float] = None,
                    return_top_percentile: Optional[float] = None):
    """Calculate optimal action for the given sequence model."""
    obs, act, rew = inputs['observations'], inputs['actions'], inputs['rewards']
    assert len(obs.shape) == 5
    assert len(act.shape) == 2
    inputs = {
        'observations': obs,
        'actions': act,
        'rewards': rew,
        'returns-to-go': jnp.zeros_like(act)
    }
    sequence_length = obs.shape[1]
    # Use samples from the last timestep.
    timestep = -1
    # A biased sampling function that prefers sampling larger returns.
    def ret_sample_fn(rng, logits):
        assert len(logits.shape) == 2
        # Add optimality bias.
        if opt_weight > 0.0:
        # Calculate log of P(optimality=1|return) := exp(return) / Z.
        logits_opt = torch.linspace(0, 1, logits.shape[1])
        logits_opt = torch.repeat_interleave(logits_opt[None, :], logits.shape[0], dim=0) # jnp.repeat(logits_opt[None, :], logits.shape[0], axis=0)
        # Sample from log[P(optimality=1|return)*P(return)].
        logits = logits + opt_weight * logits_opt
        logits = jnp.repeat(logits[None, ...], num_samples, axis=0)
        ret_sample, rng = sample_from_logits(
            rng,
            logits,
            temperature=return_temperature,
            top_percentile=return_top_percentile)
        # Pick the highest return sample.
        ret_sample = jnp.max(ret_sample, axis=0)
        # Convert return tokens into return values.
        ret_sample = decode_return(ret_sample, return_range)
        return ret_sample, rng

    # Set returns-to-go with an (optimistic) autoregressive sample.
    if single_return_token:
        # Since only first return is used by the model, only sample that (faster).
        ret_logits = logits_fn(rng, inputs)['return_logits'][:, 0, :]
        ret_sample, rng = ret_sample_fn(rng, ret_logits)
        inputs['returns-to-go'] = inputs['returns-to-go'].at[:, 0].set(ret_sample)
    else:
        # Auto-regressively regenerate all return tokens in a sequence.
        ret_logits_fn = lambda rng, input: logits_fn(rng, input)['return_logits']
        ret_sample, rng = autoregressive_generate(
            rng,
            ret_logits_fn,
            inputs,
            'returns-to-go',
            sequence_length,
            sample_fn=ret_sample_fn)
        inputs['returns-to-go'] = ret_sample

    # Generate a sample from action logits.
    act_logits = logits_fn(rng, inputs)['action_logits'][:, timestep, :]
    act_sample, rng = sample_from_logits(
        rng,
        act_logits,
        temperature=action_temperature,
        top_percentile=action_top_percentile)
    return act_sample, rng