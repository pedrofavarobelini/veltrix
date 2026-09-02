"""Risk Console — interface local do Risk Engine V2.

Este pacote e APRESENTACAO. Ele nao decide risco, nao calcula gate e nao
executa operacao alguma: chama o mesmo core que a API HTTP chama e mostra o
que voltou.

    Console  ->  Risk Service  ->  Policy/Gate  ->  resultado  ->  Console

A interface principal do Veltrix (SPA React) nao foi tocada. O Risk Engine
tem console proprio porque o publico dele e outro: alguem no terminal, antes
de executar um prompt, querendo saber o que vai acontecer.
"""
