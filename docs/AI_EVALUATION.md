# AI Evaluation

AI features are evaluated as probabilistic components, not authority systems.

## Evaluation dimensions
- factuality and evidence grounding
- structured-output validity
- prompt-injection resistance
- tenant-isolation resistance
- policy adherence
- harmful/out-of-scope action rate
- consistency/regression
- latency and cost
- human override effectiveness

## Release gate
A model/prompt change that can alter outbound decisions requires regression evaluation against representative cases. Failing or ambiguous evaluations must not silently promote a more autonomous behavior.