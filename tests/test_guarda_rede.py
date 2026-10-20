"""A guarda do conftest impede qualquer teste de falar com host externo."""
import socket
import threading
import urllib.request

import pytest


def test_urlopen_para_fora_e_bloqueado():
    with pytest.raises(AssertionError, match="example.com"):
        urllib.request.urlopen("https://example.com/", timeout=2)


def test_socket_para_fora_e_bloqueado():
    with pytest.raises(AssertionError, match="example.com"):
        socket.create_connection(("example.com", 443), timeout=2)


def test_httplib2_para_fora_e_bloqueado():
    import httplib2
    with pytest.raises(AssertionError):
        httplib2.Http(timeout=2).request("https://www.googleapis.com/youtube/v3/channels")


def test_conexao_local_continua_permitida():
    servidor = socket.socket()
    servidor.bind(("127.0.0.1", 0))
    servidor.listen(1)
    porta = servidor.getsockname()[1]
    aceito = []
    t = threading.Thread(target=lambda: aceito.append(servidor.accept()[0]))
    t.start()
    cliente = socket.create_connection(("127.0.0.1", porta), timeout=2)
    t.join(2)
    cliente.close()
    aceito[0].close()
    servidor.close()
    assert aceito
