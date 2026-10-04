from provider_mesh import provider_capability
def test_listmonk_adapter_contract(): assert provider_capability("listmonk")["supported"]
def test_unknown_provider_rejected(): assert not provider_capability("unknown")["supported"]
