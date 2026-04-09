from flask import Flask, render_template_string, jsonify
import threading
import datetime
import time
import asyncio

app = Flask(__name__)

DADOS_BOT = {
    'online': False,
    'iniciado_em': None,
    'servidores': [],
    'enquetes_pendentes': 0,
    'total_votos': 0,
    'ultimo_pedido': None
}

STATUS_GLOBAL = {
    'enquetes': [],
    'votos': {},
    'usuarios_monitorados': [],
    'usuarios_votaram': []
}


def get_status():
    dados = DADOS_BOT.copy()
    
    if dados['iniciado_em']:
        uptime = datetime.datetime.now() - dados['iniciado_em']
        dados['uptime'] = str(uptime).split('.')[0]
    else:
        dados['uptime'] = "N/A"
    
    dados['status'] = "🟢 Online" if dados['online'] else "🔴 Offline"
    
    dados.update(STATUS_GLOBAL.copy())
    
    return dados


@app.route('/')
def index():
    dados = get_status()
    return render_template_string(TEMPLATE_HTML, **dados)


@app.route('/api/status')
def api_status():
    return jsonify(get_status())


@app.route('/api/refresh')
def api_refresh():
    return jsonify(get_status())


def iniciar_dashboard(host='0.0.0.0', port=5000):
    threading.Thread(target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False), daemon=True).start()


def atualizar_status(online=None, servidores=None, enquetes_pendentes=None, total_votos=None, ultimo_pedido=None):
    if online is not None:
        DADOS_BOT['online'] = online
        if online and not DADOS_BOT['iniciado_em']:
            DADOS_BOT['iniciado_em'] = datetime.datetime.now()
    if servidores is not None:
        DADOS_BOT['servidores'] = servidores
    if enquetes_pendentes is not None:
        DADOS_BOT['enquetes_pendentes'] = enquetes_pendentes
    if total_votos is not None:
        DADOS_BOT['total_votos'] = total_votos
    if ultimo_pedido is not None:
        DADOS_BOT['ultimo_pedido'] = ultimo_pedido


def atualizar_enquetes(enquetes):
    STATUS_GLOBAL['enquetes'] = enquetes


def atualizar_votos(votos):
    STATUS_GLOBAL['votos'] = votos


def atualizar_usuarios_monitorados(usuarios):
    STATUS_GLOBAL['usuarios_monitorados'] = usuarios


def atualizar_usuarios_votaram(usuarios):
    STATUS_GLOBAL['usuarios_votaram'] = usuarios


TEMPLATE_HTML = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🍴 Bot Marmita - Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a1a2e; color: #eee; min-height: 100vh; }
        .container { max-width: 900px; margin: 0 auto; padding: 20px; }
        header { display: flex; justify-content: space-between; align-items: center; padding: 20px; background: #16213e; border-radius: 10px; margin-bottom: 20px; }
        header h1 { font-size: 1.5rem; }
        .status-badge { padding: 8px 16px; border-radius: 20px; font-weight: bold; }
        .online { background: #00c853; color: #000; }
        .offline { background: #ff1744; color: #fff; }
        
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }
        .card { background: #16213e; border-radius: 10px; padding: 20px; }
        .card h2 { font-size: 1.1rem; color: #00d9ff; margin-bottom: 15px; border-bottom: 1px solid #00d9ff33; padding-bottom: 10px; }
        .card p { margin: 8px 0; }
        .label { color: #888; font-size: 0.9rem; }
        .value { font-size: 1.1rem; font-weight: bold; }
        
        .voto-item { display: flex; justify-content: space-between; padding: 10px; background: #0f3460; border-radius: 5px; margin: 8px 0; }
        .voto-item .prato { flex: 1; }
        .voto-item .count { background: #00d9ff; color: #000; padding: 2px 10px; border-radius: 10px; font-weight: bold; }
        
        .info-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #ffffff11; }
        
        .refresh-btn { background: #00d9ff; color: #000; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; margin-top: 10px; }
        .refresh-btn:hover { background: #00b8d4; }
        
        .no-data { color: #666; font-style: italic; text-align: center; padding: 20px; }
        
        .votaram { color: #00c853; }
        .nao-votaram { color: #ff9100; }
        
        .timestamp { font-size: 0.8rem; color: #666; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🍴 Bot Marmita - Dashboard</h1>
            <span class="status-badge {{ 'online' if online else 'offline' }}">{{ status }}</span>
        </header>
        
        <div class="grid">
            <div class="card">
                <h2>📊 Status Geral</h2>
                <div class="info-row">
                    <span class="label">Uptime:</span>
                    <span class="value">{{ uptime }}</span>
                </div>
                <div class="info-row">
                    <span class="label">Servidores:</span>
                    <span class="value">{{ servidores|length }}</span>
                </div>
                <div class="info-row">
                    <span class="label">Enquetes Ativas:</span>
                    <span class="value">{{ enquetes_pendentes }}</span>
                </div>
                <div class="info-row">
                    <span class="label">Total Votos:</span>
                    <span class="value">{{ total_votos }}</span>
                </div>
                {% if ultimo_pedido %}
                <div class="info-row">
                    <span class="label">Último Pedido:</span>
                    <span class="value">{{ ultimo_pedido }}</span>
                </div>
                {% endif %}
                <button class="refresh-btn" onclick="refresh()">🔄 Atualizar</button>
                <p class="timestamp">Última atualização: <span id="last-update">{{ "agora" }}</span></p>
            </div>
            
            <div class="card">
                <h2>🏠 Servidores</h2>
                {% if servidores %}
                    {% for srv in servidores %}
                    <div class="info-row">
                        <span>{{ srv.name }}</span>
                    </div>
                    {% endfor %}
                {% else %}
                    <p class="no-data">Nenhum servidor conectado</p>
                {% endif %}
            </div>
            
            <div class="card">
                <h2>🗳️ Votos</h2>
                {% if votos %}
                    {% for prato, count in votos.items() %}
                    <div class="voto-item">
                        <span class="prato">{{ prato }}</span>
                        <span class="count">{{ count }}</span>
                    </div>
                    {% endfor %}
                {% else %}
                    <p class="no-data">Nenhum voto registrado ainda</p>
                {% endif %}
            </div>
            
            <div class="card">
                <h2>👥 Usuários Monitorados</h2>
                <div class="info-row">
                    <span class="label">Total:</span>
                    <span class="value">{{ usuarios_monitorados|length }}</span>
                </div>
                <div class="info-row">
                    <span class="label">Votaram:</span>
                    <span class="value votaram">{{ usuarios_votaram|length }}</span>
                </div>
                <div class="info-row">
                    <span class="label">Faltam:</span>
                    <span class="value nao-votaram">{{ usuarios_monitorados|length - usuarios_votaram|length }}</span>
                </div>
                {% if usuarios_monitorados %}
                <details style="margin-top: 15px;">
                    <summary style="cursor: pointer; color: #00d9ff;">Ver lista</summary>
                    <div style="margin-top: 10px; font-size: 0.85rem;">
                        {% for uid in usuarios_monitorados %}
                        <div style="padding: 3px 0;">
                            {% if uid in usuarios_votaram %}
                            <span class="votaram">✓</span>
                            {% else %}
                            <span class="nao-votaram">○</span>
                            {% endif %}
                            <code>{{ uid }}</code>
                        </div>
                        {% endfor %}
                    </div>
                </details>
                {% endif %}
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 30px; color: #666; font-size: 0.85rem;">
            <p>Bot Marmita - Netsul Informática</p>
            <p>Desenvolvido para automação de pedidos de almoço</p>
        </div>
    </div>
    
    <script>
        function refresh() {
            fetch('/api/refresh')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('last-update').textContent = new Date().toLocaleTimeString('pt-BR');
                    location.reload();
                });
        }
        
        setInterval(refresh, 30000);
    </script>
</body>
</html>
'''


if __name__ == '__main__':
    iniciar_dashboard()
    print("🌐 Dashboard iniciado em http://localhost:5000")
    print("Pressione Ctrl+C para encerrar")
    while True:
        time.sleep(1)
