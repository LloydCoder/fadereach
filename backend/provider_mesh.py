"""Provider mesh contract."""
SUPPORTED={"listmonk","ses","postmark","sendgrid","mailgun","smtp"}
def provider_capability(provider_type:str)->dict:
 return {"provider":provider_type,"supported":provider_type in SUPPORTED,"contract":"OutboundProvider.v1","requires_idempotency":True,"requires_health":True}
