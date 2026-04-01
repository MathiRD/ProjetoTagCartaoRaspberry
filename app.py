import RPi.GPIO as GPIO
from datetime import datetime, date
import time
import signal
import sys
import threading
import io
import csv
from collections import defaultdict
from flask import Flask, jsonify, render_template, Response

# CONFIGURAÇÃO DOS PINOS GPIO

LED_VERDE    = 5
LED_VERMELHO = 3

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(LED_VERDE,    GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(LED_VERMELHO, GPIO.OUT, initial=GPIO.LOW)

from mfrc522 import SimpleMFRC522
leitorRfid = SimpleMFRC522()

# ──────────────────────────────────────────────
# COLABORADORES
# ──────────────────────────────────────────────
COLABORADORES = {
    839593905989: {"nome": "Matheus Durigon", "acesso": True},
    909009092257: {"nome": "Erick De Nardi",  "acesso": False},
}

# ESTADO DO SISTEMA
registros                  = defaultdict(list)
dentro_da_sala             = {}
tentativas_nao_autorizadas = defaultdict(int)
tentativas_invasao         = defaultdict(int)
log_eventos                = [] # lista de dicts para o frontend

# Debounce: mesma tag só processada novamente após DEBOUNCE_SEG segundos
DEBOUNCE_SEG = 3
_ultima_leitura: dict = {}

def _log(tipo: str, mensagem: str, nome: str = ""):
    log_eventos.append({
        "hora":      datetime.now().strftime("%H:%M:%S"),
        "tipo":      tipo,        # "entrada" | "saida" | "negado" | "invasao"
        "mensagem":  mensagem,
        "nome":      nome,
    })

# HELPERS DE LED  (rodam em thread para não bloquear Flask)
def _run(fn):
    t = threading.Thread(target=fn, daemon=True)
    t.start()

def led_verde_solido(seg=5):
    def _():
        GPIO.output(LED_VERDE, GPIO.HIGH); time.sleep(seg); GPIO.output(LED_VERDE, GPIO.LOW)
    _run(_)

def led_verde_breve(seg=2):
    def _():
        GPIO.output(LED_VERDE, GPIO.HIGH); time.sleep(seg); GPIO.output(LED_VERDE, GPIO.LOW)
    _run(_)

def led_vermelho_solido(seg=5):
    def _():
        GPIO.output(LED_VERMELHO, GPIO.HIGH); time.sleep(seg); GPIO.output(LED_VERMELHO, GPIO.LOW)
    _run(_)

def led_vermelho_pisca(vezes=10, intervalo=0.3):
    def _():
        for _ in range(vezes):
            GPIO.output(LED_VERMELHO, GPIO.HIGH); time.sleep(intervalo)
            GPIO.output(LED_VERMELHO, GPIO.LOW);  time.sleep(intervalo)
    _run(_)

# LÓGICA RFID
def _ja_entrou_hoje(tag_id):
    hoje = date.today()
    for reg in registros[tag_id]:
        if reg["entrada"].date() == hoje:
            return True
    return False

def processar_leitura(tag_id: int):
    agora = datetime.now()

    if tag_id not in COLABORADORES:
        tentativas_invasao[tag_id] += 1
        msg = f"Identificação não encontrada! Tag: {tag_id} (ocorrência nº {tentativas_invasao[tag_id]})"
        print(f"\n⚠️  {msg}")
        _log("invasao", msg)
        led_vermelho_pisca(10)
        return

    colaborador = COLABORADORES[tag_id]
    nome = colaborador["nome"]

    if not colaborador["acesso"]:
        tentativas_nao_autorizadas[tag_id] += 1
        msg = f"Você não tem acesso a este projeto, {nome}. (Tentativa nº {tentativas_nao_autorizadas[tag_id]})"
        print(f"\n🔴 {msg}")
        _log("negado", msg, nome)
        led_vermelho_solido(5)
        return

    if tag_id in dentro_da_sala:
        entrada = dentro_da_sala.pop(tag_id)
        for reg in reversed(registros[tag_id]):
            if reg["saida"] is None:
                reg["saida"] = agora
                break
        duracao = agora - entrada
        minutos = int(duracao.total_seconds() // 60)
        msg = f"Até logo, {nome}! Permanência: {minutos} min"
        print(f"\n👋 {msg}")
        _log("saida", msg, nome)
        led_verde_breve(2)
        return

    ja_esteve_hoje = _ja_entrou_hoje(tag_id)
    registros[tag_id].append({"entrada": agora, "saida": None})
    dentro_da_sala[tag_id] = agora

    if ja_esteve_hoje:
        msg = f"Bem-vindo de volta, {nome}!"
    else:
        msg = f"Bem-vindo, {nome}!"

    print(f"\n🟢 {msg}")
    _log("entrada", msg, nome)
    led_verde_solido(5)

def loop_rfid():
    print("[RFID] Loop iniciado.")
    while True:
        try:
            tag_id, _ = leitorRfid.read()
            agora = time.time()
            ultima = _ultima_leitura.get(tag_id, 0)
            if agora - ultima < DEBOUNCE_SEG:
                time.sleep(0.5)
                continue
            _ultima_leitura[tag_id] = agora
            processar_leitura(tag_id)
            print("\n── Aguardando próxima leitura... ──\n")
        except Exception as e:
            print(f"[Erro na leitura]: {e}")
            time.sleep(1)

# FLASK APP
app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def api_status():
    agora = datetime.now()

    presenca = []
    for tag_id, colab in COLABORADORES.items():
        total_seg = 0.0
        sessoes = 0
        for reg in registros[tag_id]:
            saida = reg["saida"] if reg["saida"] else agora
            total_seg += (saida - reg["entrada"]).total_seconds()
            sessoes += 1
        h = int(total_seg // 3600)
        m = int((total_seg % 3600) // 60)
        s = int(total_seg % 60)
        presenca.append({
            "nome":        colab["nome"],
            "acesso":      colab["acesso"],
            "dentro":      tag_id in dentro_da_sala,
            "sessoes":     sessoes,
            "total":       f"{h:02d}h {m:02d}min {s:02d}s",
            "total_seg":   total_seg,
        })

    nao_autorizados = []
    for tag_id, qtd in tentativas_nao_autorizadas.items():
        nao_autorizados.append({
            "nome": COLABORADORES[tag_id]["nome"],
            "tentativas": qtd,
        })

    return jsonify({
        "hora":               agora.strftime("%H:%M:%S"),
        "data":               agora.strftime("%d/%m/%Y"),
        "presenca":           presenca,
        "nao_autorizados":    nao_autorizados,
        "total_invasoes":     sum(tentativas_invasao.values()),
        "log":                list(reversed(log_eventos[-50:])),
    })

@app.route("/api/relatorio/csv")
def relatorio_csv():
    agora = datetime.now()
    output = io.StringIO()
    w = csv.writer(output)

    w.writerow(["RELATÓRIO DE ACESSO — SALA DO PROJETO"])
    w.writerow([f"Gerado em: {agora.strftime('%d/%m/%Y %H:%M:%S')}"])
    w.writerow([])

    w.writerow(["TEMPO DE PERMANÊNCIA"])
    w.writerow(["Nome", "Acesso", "Sessões", "Total"])
    for tag_id, colab in COLABORADORES.items():
        total_seg = 0.0
        sessoes = 0
        for reg in registros[tag_id]:
            saida = reg["saida"] if reg["saida"] else agora
            total_seg += (saida - reg["entrada"]).total_seconds()
            sessoes += 1
        h = int(total_seg // 3600)
        m = int((total_seg % 3600) // 60)
        s = int(total_seg % 60)
        w.writerow([colab["nome"], "Sim" if colab["acesso"] else "Não",
                    sessoes, f"{h:02d}h {m:02d}min {s:02d}s"])

    w.writerow([])
    w.writerow(["TENTATIVAS NÃO AUTORIZADAS"])
    w.writerow(["Nome", "Tentativas"])
    for tag_id, qtd in tentativas_nao_autorizadas.items():
        w.writerow([COLABORADORES[tag_id]["nome"], qtd])

    w.writerow([])
    w.writerow(["TENTATIVAS DE INVASÃO (tag desconhecida)"])
    w.writerow(["Tag ID", "Tentativas"])
    for tag_id, qtd in tentativas_invasao.items():
        w.writerow([tag_id, qtd])
    w.writerow(["TOTAL", sum(tentativas_invasao.values())])

    w.writerow([])
    w.writerow(["LOG DE EVENTOS"])
    w.writerow(["Hora", "Tipo", "Mensagem"])
    for ev in log_eventos:
        w.writerow([ev["hora"], ev["tipo"], ev["mensagem"]])

    output.seek(0)
    nome_arquivo = f"relatorio_{agora.strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"}
    )

# ENCERRAMENTO
def encerrar(sig, frame):
    print("\n[Sistema encerrando...]")
    GPIO.cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, encerrar)

# MAIN
if __name__ == "__main__":
    rfid_thread = threading.Thread(target=loop_rfid, daemon=True)
    rfid_thread.start()
    app.run(host="0.0.0.0", port=5000, debug=False)