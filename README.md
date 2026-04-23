# CorsarioXxX

Fase 1 do novo CorsarioXxX: um assistente local em terminal, autenticado para uso exclusivo do dono, com respostas deterministicas para identidade e regras, chat integrado com Ollama e execucao controlada de comandos no PC.

## Objetivo da fase

- chat local de boa qualidade
- uso exclusivo por senha mestra local
- respostas fixas para identidade, regras e status
- execucao automatica de comandos seguros
- confirmacao para comandos sensiveis

## Como rodar

```powershell
cd C:\Users\heinz\Desktop\CorsarioXxX
python -m pip install -e .[dev]
python -m corsarioxxx
```

Na primeira execucao o programa cria a configuracao local e pede a senha mestra.
