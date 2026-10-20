"""Guarda de rede: nenhum teste fala com host externo.

A guarda fica no nível do socket (resolução de nome e connect), não só no urllib:
o google-api-python-client usa httplib2, e um patch que não pegou chegaria à API real
e gastaria cota do canal.
"""
import socket

import pytest

LOCAIS = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}


def _host(endereco):
    if isinstance(endereco, tuple):
        return str(endereco[0])
    return str(endereco)


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    resolver = socket.getaddrinfo
    conectar = socket.socket.connect
    conectar_ex = socket.socket.connect_ex

    def getaddrinfo(host, *args, **kwargs):
        if host is not None and str(host) not in LOCAIS:
            raise AssertionError(f"teste tentou acessar a rede: {host}")
        return resolver(host, *args, **kwargs)

    def checa(sock, endereco):
        if sock.family in (socket.AF_INET, socket.AF_INET6) and _host(endereco) not in LOCAIS:
            raise AssertionError(f"teste tentou acessar a rede: {_host(endereco)}")

    def connect(sock, endereco):
        checa(sock, endereco)
        return conectar(sock, endereco)

    def connect_ex(sock, endereco):
        checa(sock, endereco)
        return conectar_ex(sock, endereco)

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
    yield
