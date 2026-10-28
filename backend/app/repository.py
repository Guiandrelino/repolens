import base64

import httpx

from .config import get_settings

IGNORED = {"node_modules", "vendor", "dist", "build", ".next", "coverage", ".git"}
EXTENSIONS = (".js", ".jsx", ".ts", ".tsx", ".json", ".md")
DEMO_FILES = {
    "src/api/users.js": "export async function getUser(req, res) {\n  const user = await db.users.findById(req.params.id);\n  res.json(user);\n}\n",
    "src/utils/storage.js": 'export function saveSession(token) {\n  localStorage.setItem("session_token", token);\n}\n',
    "package.json": '{\n  "name": "example-app",\n  "scripts": { "start": "node src/index.js" }\n}\n',
}


class Repository:
    def __init__(self, files, sha, total_files=0, truncated=False):
        self.files = files
        self.sha = sha
        self.total_files = total_files or len(files)
        self.truncated = truncated
        self.read_paths = set()

    def tool(self, name, args):
        if name == "list_files":
            return "\n".join(self.files)
        if name == "read_file":
            path = args.get("path", "")
            if path not in self.files:
                return "Arquivo não disponível no escopo."
            start = max(1, int(args.get("start_line", 1)))
            end = min(start + 119, int(args.get("end_line", start + 119)))
            self.read_paths.add(path)
            return "\n".join(
                f"{i}: {line}" for i, line in enumerate(self.files[path].splitlines(), 1) if start <= i <= end
            )
        if name == "search_code":
            query = str(args.get("query", ""))[:120]
            matches = []
            for path, content in self.files.items():
                for i, line in enumerate(content.splitlines(), 1):
                    if query and query.lower() in line.lower():
                        matches.append(f"{path}:{i}: {line[:300]}")
            return "\n".join(matches[:40]) or "Nenhum resultado."
        return "Ferramenta desconhecida."


def load_repository(url):
    settings = get_settings()
    owner_repo = url.removeprefix("https://github.com/")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    with httpx.Client(
        base_url="https://api.github.com", headers=headers, timeout=25, follow_redirects=False
    ) as client:

        def get(path):
            response = client.get(path)
            if response.status_code == 404:
                raise ValueError("Repositório público não encontrado.")
            if response.status_code in (403, 429):
                raise ValueError(
                    "Limite da API do GitHub atingido. Tente mais tarde ou configure GITHUB_TOKEN."
                )
            response.raise_for_status()
            return response.json()

        info = get(f"/repos/{owner_repo}")
        if info.get("private"):
            raise ValueError("Apenas repositórios públicos são permitidos.")
        branch = httpx.URL("/", params={"ref": info["default_branch"]}).params["ref"]
        # Resolve HEAD sem interpolar o nome da branch em caminhos.
        response = client.get(f"/repos/{owner_repo}/commits", params={"sha": branch, "per_page": 1})
        response.raise_for_status()
        commits = response.json()
        if not commits:
            raise ValueError("Repositório vazio.")
        sha = commits[0]["sha"]
        tree = get(f"/repos/{owner_repo}/git/trees/{sha}?recursive=1")
        if tree.get("truncated"):
            raise ValueError("Repositório grande demais para este MVP.")
        candidates = [
            item
            for item in tree["tree"]
            if item["type"] == "blob"
            and item.get("mode") != "120000"
            and not IGNORED.intersection(item["path"].split("/"))
            and item["path"].endswith(EXTENSIONS)
            and not item["path"].endswith(("lock.json", ".min.js"))
            and item.get("size", 0) <= 40_000
        ]
        candidates.sort(
            key=lambda item: (not item["path"].endswith((".js", ".ts", ".jsx", ".tsx")), item["path"])
        )
        files, size = {}, 0
        for item in candidates[: settings.max_files]:
            if size + item.get("size", 0) > settings.max_source_bytes:
                break
            blob = get(f"/repos/{owner_repo}/git/blobs/{item['sha']}")
            raw = base64.b64decode(blob["content"])
            if size + len(raw) > settings.max_source_bytes:
                break
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            files[item["path"]] = content
            size += len(raw)
        if not files:
            raise ValueError("Nenhum arquivo JS/TS ou documento elegível encontrado.")
        return Repository(files, sha, len(candidates), len(files) < len(candidates))
