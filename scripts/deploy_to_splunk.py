import subprocess
import requests
import yaml
import argparse
import urllib3

# Desactivar advertencias de certificados SSL (común en laboratorios)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def convert_sigma_to_splunk(rule_path):
    print(f"[*] Convirtiendo regla Sigma: {rule_path}")
    result = subprocess.run(
        ["sigma", "convert", "-t", "splunk", "--without-pipeline", rule_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Error al convertir: {result.stderr}")
        return None
    
    query = result.stdout.strip()
    print(f"[*] Consulta SPL generada: {query}")
    return query

def deploy_to_splunk(query, rule_path, splunk_host, splunk_port, username, password):
    # Extraer el nombre de la regla del archivo YAML
    with open(rule_path, 'r') as f:
        rule_data = yaml.safe_load(f)
    rule_title = f"Sigma - {rule_data.get('title', 'Custom Rule')}"

    print(f"[*] Desplegando alerta '{rule_title}' en Splunk...")

    url = f"https://{splunk_host}:{splunk_port}/services/saved/searches"
    
    # Datos de la alerta en Splunk
    payload = {
        "name": rule_title,
        "search": f"index=* {query}",
        "cron_schedule": "*/5 * * * *", # Cada 5 minutos
        "is_scheduled": "1",
        "alert_type": "number of events",
        "alert_comparator": "greater than",
        "alert_threshold": "0",
        "alert.severity": "4", # 4 = High en Splunk
        "action.email": "0",
        "action.notable": "1"  # Enviar a Triggered Alerts
    }

    # Hacer la petición a la API REST
    response = requests.post(
        url,
        auth=(username, password),
        data=payload,
        verify=False # Ignorar SSL (self-signed certs)
    )

    if response.status_code == 201:
        print(f"✅ ¡Alerta '{rule_title}' creada exitosamente en Splunk!")
    else:
        print(f"❌ Error al crear la alerta: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Despliega reglas Sigma en Splunk automáticamente.")
    parser.add_argument("--rule", required=True, help="Ruta al archivo YAML de Sigma")
    parser.add_argument("--host", required=True, help="IP o dominio de Splunk")
    parser.add_argument("--port", default="8089", help="Puerto de la API (por defecto 8089)")
    parser.add_argument("--user", default="admin", help="Usuario de Splunk")
    parser.add_argument("--password", required=True, help="Contraseña de Splunk")

    args = parser.parse_args()

    # 1. Convertir
    splunk_query = convert_sigma_to_splunk(args.rule)
    
    # 2. Desplegar
    if splunk_query:
        deploy_to_splunk(splunk_query, args.rule, args.host, args.port, args.user, args.password)