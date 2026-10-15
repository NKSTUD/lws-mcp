# lws-mcp

[![CI](https://github.com/NKSTUD/lws-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/NKSTUD/lws-mcp/actions/workflows/ci.yml)
[![Licence : MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/lws-mcp.svg)](https://pypi.org/project/lws-mcp/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

[English](README.md) · **Français**

Un serveur [MCP](https://modelcontextprotocol.io) pour l'API client de [LWS](https://www.lws.fr). Gérez vos domaines, zones DNS, hébergements et votre compte depuis Claude, Cursor ou tout client MCP :

> *« Ajoute à exemple.fr les CNAME que Stripe m'a donnés, puis dis-moi quand ils répondent. »*

Il couvre toute l'[API client LWS](https://api.lws.fr/api-client/lws-client-api) (29 routes), plus une vérification de propagation via un résolveur public.

> Projet communautaire, sans lien avec LWS.

## Outils

| Domaine | Outils |
| --- | --- |
| **DNS** | `get_dns_zone` · `add_dns_record` · `update_dns_record` · `delete_dns_record` · `check_dns_propagation` |
| **Domaines** | `get_domain` · `check_domain_availability` · `list_tlds` · `update_nameservers` · `set_transfer_protection` · `request_transfer_authcode` · `create_domain_redirect` · `delete_domain_redirect` |
| **Hébergement** | `list_hostings` · `get_hosting` · `list_hosting_prices` · `get_renewal_prices` · `set_auto_renew` · `buy_hosting`¹ · `renew_hosting`¹ |
| **Compte** | `get_account_balance` · `get_purchase_history` · `list_contacts` · `get_contact` · `create_contact` · `update_contact` · `add_test_credit_to_contact`² · `add_test_credit_to_account`² |
| **Demandes** | `list_requests` · `list_pending_requests` |

¹ Payants : désactivés sauf avec `LWS_ENABLE_PURCHASES=true`. ² En mode test uniquement.

Les noms d'enregistrements DNS peuvent être donnés en entier (`_dmarc.exemple.fr`) : ils sont raccourcis comme la zone LWS les attend (`_dmarc`, `@`).

## Sécurité

Un assistant qui touche à vos DNS peut couper un site ou une boîte mail, et un assistant qui peut acheter peut dépenser de l'argent. Donc :

- **Achats désactivés par défaut.** `buy_hosting` et `renew_hosting` n'existent qu'avec `LWS_ENABLE_PURCHASES=true`.
- **Mode lecture seule.** `LWS_READ_ONLY=true` retire tous les outils qui modifient quelque chose.
- **Indications pour le client.** Chaque outil déclare s'il lit, écrit ou supprime ([annotations](https://modelcontextprotocol.io/specification/2025-06-18/server/tools#tool-annotations)), pour que le client demande confirmation.
- **Environnement de test.** `LWS_TEST_MODE=true` envoie toutes les requêtes au bac à sable LWS.
- **La clé reste chez vous.** Elle ne part que vers `api.lws.net`, n'est jamais journalisée ni renvoyée au modèle.

## Prérequis

- Un compte LWS et sa clé API : [LWS Panel](https://www.lws.fr/panel) → votre numéro (LWS-XXXXXX, en haut à droite) → **Api LWS** → **Clé API en mode PRODUCTION** → *voir*. [Guide LWS](https://aide.lws.fr/a/1943).
- L'adresse IP publique de la machine qui lance le serveur, autorisée sur la même page **Api LWS**. Sinon chaque appel échoue avec `bad source <votre IP>`.
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (il installe Python et le serveur pour vous).

## Installation

Tous les clients lancent la même commande, `uvx lws-mcp`, avec `LWS_LOGIN` et `LWS_API_KEY` dans son environnement (réglages facultatifs dans [Configuration](#configuration)).

[![Installer dans Cursor](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en/install-mcp?name=lws&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJsd3MtbWNwIl0sImVudiI6eyJMV1NfTE9HSU4iOiIiLCJMV1NfQVBJX0tFWSI6IiJ9fQ%3D%3D)
[![Installer dans VS Code](https://img.shields.io/badge/VS_Code-Install-0098FF?logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=lws&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22lws-mcp%22%5D%2C%22env%22%3A%7B%22LWS_LOGIN%22%3A%22%22%2C%22LWS_API_KEY%22%3A%22%22%7D%7D)

Les boutons laissent `LWS_LOGIN` et `LWS_API_KEY` vides : remplissez-les après l'installation.

<details open>
<summary><b>Claude Code</b></summary>

```bash
claude mcp add lws \
  -e LWS_LOGIN=123456 \
  -e LWS_API_KEY=votre-cle-api \
  -- uvx lws-mcp
```
</details>

<details>
<summary><b>Codex</b> (CLI, extension IDE et application)</summary>

```bash
codex mcp add lws \
  --env LWS_LOGIN=123456 \
  --env LWS_API_KEY=votre-cle-api \
  -- uvx lws-mcp
```

Ou dans `~/.codex/config.toml` :

```toml
[mcp_servers.lws]
command = "uvx"
args = ["lws-mcp"]
env = { LWS_LOGIN = "123456", LWS_API_KEY = "votre-cle-api" }
```
</details>

<details>
<summary><b>Cursor</b></summary>

Utilisez le bouton ci-dessus, ou ajoutez à `~/.cursor/mcp.json` (tous les projets) ou `.cursor/mcp.json` (un projet) :

```json
{
  "mcpServers": {
    "lws": {
      "command": "uvx",
      "args": [
        "lws-mcp"
      ],
      "env": {
        "LWS_LOGIN": "123456",
        "LWS_API_KEY": "votre-cle-api"
      }
    }
  }
}
```
</details>

<details>
<summary><b>VS Code</b> (GitHub Copilot)</summary>

```bash
code --add-mcp '{"name":"lws","command":"uvx","args":["lws-mcp"],"env":{"LWS_LOGIN":"123456","LWS_API_KEY":"votre-cle-api"}}'
```

Ou dans `.vscode/mcp.json` :

```json
{
  "servers": {
    "lws": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "lws-mcp"
      ],
      "env": {
        "LWS_LOGIN": "123456",
        "LWS_API_KEY": "votre-cle-api"
      }
    }
  }
}
```
</details>

<details>
<summary><b>Claude Desktop · Windsurf · Gemini CLI · autres</b></summary>

Ajoutez ce bloc au fichier MCP du client :

| Client | Fichier |
| --- | --- |
| Claude Desktop | Réglages → Développeur → Modifier la config (`claude_desktop_config.json`) |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |
| Gemini CLI | `~/.gemini/settings.json` |
| Cline, Roo Code, Zed… | leurs réglages MCP, même format |

```json
{
  "mcpServers": {
    "lws": {
      "command": "uvx",
      "args": [
        "lws-mcp"
      ],
      "env": {
        "LWS_LOGIN": "123456",
        "LWS_API_KEY": "votre-cle-api"
      }
    }
  }
}
```
</details>

## Configuration

| Variable | Défaut | Description |
| --- | --- | --- |
| `LWS_LOGIN` | *obligatoire* | Identifiant du compte LWS (les chiffres de LWS-XXXXXX). |
| `LWS_API_KEY` | *obligatoire* | Clé API de production. |
| `LWS_TEST_API_KEY` | | Clé de test, utilisée à la place de `LWS_API_KEY` en mode test. |
| `LWS_TEST_MODE` | `false` | Envoie les requêtes à l'environnement de test LWS. |
| `LWS_READ_ONLY` | `false` | N'expose que les outils de lecture. |
| `LWS_ENABLE_PURCHASES` | `false` | Expose `buy_hosting` et `renew_hosting`. |
| `LWS_TIMEOUT` | `30` | Délai d'attente des requêtes, en secondes. |
| `LWS_BASE_URL` | `https://api.lws.net/v1` | Adresse de l'API. |

## Bon à savoir

- **Actions différées.** Changement de serveurs de noms, protection de transfert, code de transfert, achats et renouvellements sont traités en arrière-plan : suivez-les avec `list_pending_requests`.
- **Propagation.** Un changement DNS peut mettre de quelques minutes à quelques heures à être vu partout. `check_dns_propagation` montre ce que voit le 1.1.1.1 de Cloudflare à l'instant.
- **Les identifiants changent.** LWS remplace un enregistrement modifié sous un nouvel identifiant. `add_dns_record` et `update_dns_record` renvoient l'identifiant à jour.
- **Limite de requêtes.** LWS refuse les rafales (une quinzaine d'appels d'affilée) avec `Invalid input (rate limit)` : attendez une minute et recommencez.
- **TTL acceptés.** 900, 1800, 3600, 7200, 21600, 43200 ou 86400 secondes.

## Développement

```bash
git clone https://github.com/NKSTUD/lws-mcp && cd lws-mcp
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

Pour essayer sur votre compte avec le [MCP Inspector](https://github.com/modelcontextprotocol/inspector), identifiants dans un `.env` local (voir [.env.example](.env.example)) :

```bash
npx @modelcontextprotocol/inspector uv run --env-file .env lws-mcp
```

Pour ajouter un outil ou corriger un bug, voir [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

[MIT](LICENSE)
