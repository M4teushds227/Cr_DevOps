import os
import re
import json
import base64
import requests
from html import unescape
from datetime import datetime
from urllib.parse import quote


def html_to_plain_text(html_str: str) -> str:
    """Convert Azure DevOps HTML description to clean plain text for editing."""
    if not html_str:
        return ""
    text = html_str
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</div>\s*<div[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>\s*<p[^>]*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</div>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    # Remove excessive trailing newlines
    return text.strip("\r\n")


def plain_text_to_html(plain_str: str) -> str:
    """Convert plain text lines back into clean HTML divs for Azure DevOps."""
    if not plain_str:
        return ""
    lines = plain_str.splitlines()
    html_parts = []
    for line in lines:
        escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if escaped.startswith(" "):
            escaped = "&nbsp;" + escaped[1:]
        if not escaped:
            html_parts.append("<div><br></div>")
        else:
            html_parts.append(f"<div>{escaped}</div>")
    return "".join(html_parts)


class AzureDevOpsClient:
    # Categorized Dashboards for One_FrontEnd (with "Equipe de Desenvolvimento - Overview" as the default)
    DASHBOARDS_MAP = {
        "📋 Equipe de Desenvolvimento - Overview": [
            {"query_id": "540a1a90-e519-4703-87cb-4d48bfeec5ce", "title": "DE - Demandas Erros", "tag": "DE - Demandas Erros"},
            {"query_id": "5d29b2ac-eeab-45b0-ad7a-f0bf8e6c75ae", "title": "AES - Acompanhamento de Erros sem Solução", "tag": "AES - Acompanhamento de Erros sem Solução"},
            {"query_id": "65eeee58-487f-4401-ab3b-8d89ec16c8e0", "title": "PLib - Pendentes de Liberação", "tag": "PLib - Pendentes de Liberação"},
            {"query_id": "59cccee1-f462-4ffb-8e66-ff39841bf6f9", "title": "RR - Renovação relatórios", "tag": "RR - Renovação relatórios"},
            {"query_id": "aa30b9f5-5111-4004-b3a7-d17c1f480194", "title": "TVali - Testes de Validação", "tag": "TVali - Testes de Validação"},
            {"query_id": "0718f4ad-52f6-4d85-b168-c9a3154508af", "title": "Dm - Demandas Melhorias", "tag": "Dm - Demandas Melhorias"},
            {"query_id": "678685fe-6780-4b86-8961-8581e78cc79a", "title": "PClis - Pedidos de Clientes", "tag": "PClis - Pedidos de Clientes"},
            {"query_id": "18071462-e76c-4784-8b82-e2b8f44eb63b", "title": "Sug - Sugestão", "tag": "Sug - Sugestão"},
            {"query_id": "9bf32164-fa8c-4794-a2a1-f953e839f038", "title": "Cr - Cadastro Rapido", "tag": "Cr - Cadastro Rapido"},
            {"query_id": "663ee8ab-5e8b-4213-b3f9-41e1b2f9238a", "title": "Feitos (Últimos 30 dias)", "tag": ""},
        ],
        "🎧 Dashboard - Equipe de Suporte": [
            {"query_id": "fa26aad6-f969-488c-b114-1c1bff72b149", "title": "Demandas Sistema Suporte", "tag": "DemandasSistemaSuporte"},
            {"query_id": "6b9e0622-8cbb-43b3-8967-21d81b55d456", "title": "Erros Sistema Suporte", "tag": "ErrosSistemaSuporte"},
            {"query_id": "15307463-70ae-4803-8b28-0e315c231bff", "title": "Demandas Mobilidade Suporte", "tag": "DemandasMobilidadeSuporte"},
            {"query_id": "aa36c843-7da9-4539-b93c-9081ed4b0f2f", "title": "Erros Mobilidade Suporte", "tag": "ErrosMobilidadeSuporte"},
            {"query_id": "53a308ec-b2b5-48a8-ab61-ffcf7234ff36", "title": "SugestãoMelhoriaSuporte", "tag": "SugestãoMelhoriaSuporte"},
            {"query_id": "840bc3bd-5d40-4f15-979f-262322811fc4", "title": "DemandasCompletasSuporte", "tag": ""},
        ],
        "⚙️ Dashboard - Acompanhamento Geral & Sprint": [
            {"query_id": "eb1643d1-ae33-405c-ae84-efc8c651755c", "title": "Em execução", "tag": ""},
            {"query_id": "74141760-0853-47d3-81bb-dfee9c8a1fe4", "title": "Pendentes de Publicação", "tag": ""},
            {"query_id": "41112f54-2b64-4659-9881-5e342635eed3", "title": "Próximas Tarefas", "tag": ""},
            {"query_id": "ca66a619-62a5-43ad-9999-1eb118743fad", "title": "Tarefas não avaliadas", "tag": ""},
            {"query_id": "491a784c-5f8d-4ae4-b3cf-ce73c771a96d", "title": "Bugs resolvidos", "tag": ""},
            {"query_id": "4771c5cf-286e-4e2a-ac3c-15872ab339cd", "title": "Concluídos - GERAL", "tag": ""},
            {"query_id": "a1b5b70b-dd9c-4b24-a58d-0bb813fd9469", "title": "Assigned to me", "tag": ""},
        ]
    }

    OVERVIEW_PRIORITY = (
        DASHBOARDS_MAP["📋 Equipe de Desenvolvimento - Overview"]
        + DASHBOARDS_MAP["🎧 Dashboard - Equipe de Suporte"]
        + DASHBOARDS_MAP["⚙️ Dashboard - Acompanhamento Geral & Sprint"]
    )

    def __init__(self, organization: str, pat: str):
        self.organization = organization.strip()
        self.pat = pat.strip()
        self.base_url = f"https://dev.azure.com/{quote(self.organization)}"
        self._field_cache = {}

    def _get_headers(self, content_type="application/json"):
        token_bytes = f":{self.pat}".encode("utf-8")
        b64_token = base64.b64encode(token_bytes).decode("utf-8")
        return {
            "Authorization": f"Basic {b64_token}",
            "Content-Type": content_type,
            "Accept": "application/json"
        }

    def test_connection(self, project: str):
        """Test authentication and check if project is accessible."""
        if not self.organization or not self.pat:
            return False, "Organização ou PAT Token não informados."

        url = f"{self.base_url}/_apis/projects/{quote(project.strip())}?api-version=7.1"
        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return True, f"Conectado com sucesso ao projeto '{data.get('name', project)}'!"
            elif resp.status_code in (203, 302):
                return False, "Token PAT inválido ou expirado. O Azure DevOps redirecionou para tela de login HTML (HTTP 203/302). Verifique se copiou o token completo."
            elif resp.status_code in (401, 403):
                return False, "Erro de autenticação (401/403). Verifique se o seu PAT Token está válido e tem permissão de 'Work Items (Read & Write)'."
            elif resp.status_code == 404:
                return False, f"Projeto '{project}' ou organização '{self.organization}' não encontrados (404)."
            else:
                return False, f"Erro HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            return False, f"Erro de conexão: {str(e)}"

    def get_projects(self):
        """Fetch list of projects in the organization."""
        if not self.organization or not self.pat:
            return []
        url = f"{self.base_url}/_apis/projects?api-version=7.1"
        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=10)
            if resp.status_code == 200:
                items = resp.json().get("value", [])
                return [p["name"] for p in items if "name" in p]
        except Exception:
            pass
        return []

    def get_work_item_fields(self, project: str, work_item_type: str):
        """Fetch fields available for a given project and work item type to map custom fields."""
        cache_key = f"{project}:{work_item_type}"
        if cache_key in self._field_cache:
            return self._field_cache[cache_key]

        url = f"{self.base_url}/{quote(project.strip())}/_apis/wit/workitemtypes/{quote(work_item_type.strip())}/fields?api-version=7.1"
        field_map = {}
        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=10)
            if resp.status_code == 200:
                fields = resp.json().get("value", [])
                for f in fields:
                    name_lower = f.get("name", "").lower().strip()
                    ref_name = f.get("referenceName", "")
                    if name_lower and ref_name:
                        field_map[name_lower] = ref_name
                        field_map[ref_name.lower()] = ref_name
                self._field_cache[cache_key] = field_map
                return field_map
        except Exception:
            pass

        url_all = f"{self.base_url}/{quote(project.strip())}/_apis/wit/fields?api-version=7.1"
        try:
            resp = requests.get(url_all, headers=self._get_headers(), timeout=10)
            if resp.status_code == 200:
                fields = resp.json().get("value", [])
                for f in fields:
                    name_lower = f.get("name", "").lower().strip()
                    ref_name = f.get("referenceName", "")
                    if name_lower and ref_name:
                        field_map[name_lower] = ref_name
                        field_map[ref_name.lower()] = ref_name
                self._field_cache[cache_key] = field_map
        except Exception:
            pass

        return field_map

    def resolve_custom_field(self, field_map: dict, display_name: str, fallback_candidates: list):
        """Find the exact referenceName for a custom field like 'Noticed At', 'Reported By', 'Urgency'."""
        dn_lower = display_name.lower().strip()
        if dn_lower in field_map:
            return field_map[dn_lower]
        for candidate in fallback_candidates:
            if candidate.lower() in field_map:
                return field_map[candidate.lower()]
        for k, ref in field_map.items():
            clean_k = k.replace(" ", "").replace("custom.", "").replace("mmtoolsprocess.", "").replace("microsoft.vsts.common.", "")
            if dn_lower.replace(" ", "") == clean_k:
                return ref
        return fallback_candidates[0] if fallback_candidates else f"Custom.{display_name.replace(' ', '')}"

    def upload_attachment(self, project: str, file_path: str, file_name: str = None):
        """Upload a binary file or image to Azure DevOps attachments endpoint."""
        if not file_name:
            file_name = os.path.basename(file_path)

        url = f"{self.base_url}/{quote(project.strip())}/_apis/wit/attachments?fileName={quote(file_name)}&api-version=7.1"
        headers = self._get_headers(content_type="application/octet-stream")

        with open(file_path, "rb") as f:
            data = f.read()

        resp = requests.post(url, headers=headers, data=data, timeout=30)
        if resp.status_code in (200, 201):
            return resp.json().get("url")
        else:
            raise Exception(f"Falha ao enviar anexo '{file_name}' (HTTP {resp.status_code}): {resp.text[:200]}")

    def create_demand(
        self,
        project: str,
        work_item_type: str,
        title: str,
        description_html: str,
        tags: str = "",
        area_path: str = "",
        iteration_path: str = "",
        noticed_at_iso: str = "",
        reported_by: str = "",
        urgency: str = "",
        attachment_paths: list = None,
        extra_details_in_desc: str = ""
    ):
        project = project.strip()
        work_item_type = work_item_type.strip()

        uploaded_attachments = []
        if attachment_paths:
            for path in attachment_paths:
                if os.path.exists(path):
                    att_name = os.path.basename(path)
                    att_url = self.upload_attachment(project, path, att_name)
                    if att_url:
                        uploaded_attachments.append((att_name, att_url))

        field_map = self.get_work_item_fields(project, work_item_type)

        noticed_ref = self.resolve_custom_field(
            field_map, "Noticed At", ["MMToolsProcess.NoticedAt", "Custom.NoticedAt", "Custom.Noticed_At"]
        )
        reported_ref = self.resolve_custom_field(
            field_map, "Reported By", ["MMToolsProcess.ReportedBy", "Custom.ReportedBy", "Custom.Reported_By", "Microsoft.VSTS.Common.ReportedBy"]
        )
        urgency_ref = self.resolve_custom_field(
            field_map, "Urgency", ["MMToolsProcess.Urgency", "Custom.Urgency", "Microsoft.VSTS.Common.Urgency", "Microsoft.VSTS.Common.Priority"]
        )

        base_ops = [
            {"op": "add", "path": "/fields/System.Title", "value": title.strip()},
            {"op": "add", "path": "/fields/System.Description", "value": description_html}
        ]

        if "microsoft.vsts.tcm.reprosteps" in field_map and work_item_type.lower() == "bug":
            base_ops.append({
                "op": "add",
                "path": "/fields/Microsoft.VSTS.TCM.ReproSteps",
                "value": description_html
            })

        if tags and tags.strip():
            base_ops.append({"op": "add", "path": "/fields/System.Tags", "value": tags.strip()})

        if area_path and area_path.strip():
            base_ops.append({"op": "add", "path": "/fields/System.AreaPath", "value": area_path.strip()})

        if iteration_path and iteration_path.strip():
            base_ops.append({"op": "add", "path": "/fields/System.IterationPath", "value": iteration_path.strip()})

        for att_name, att_url in uploaded_attachments:
            base_ops.append({
                "op": "add",
                "path": "/relations/-",
                "value": {
                    "rel": "AttachedFile",
                    "url": att_url,
                    "attributes": {"comment": f"Anexo enviado via Cadastrador Rápido DevOps ({att_name})"}
                }
            })

        custom_ops = []
        if noticed_at_iso:
            custom_ops.append({"op": "add", "path": f"/fields/{noticed_ref}", "value": noticed_at_iso})
        if reported_by and reported_by.strip():
            custom_ops.append({"op": "add", "path": f"/fields/{reported_ref}", "value": reported_by.strip()})
        if urgency and str(urgency).strip():
            urg_val = str(urgency).strip()
            urg_val_typed = int(urg_val) if urg_val.isdigit() else urg_val
            custom_ops.append({"op": "add", "path": f"/fields/{urgency_ref}", "value": urg_val_typed})

        url = f"{self.base_url}/{quote(project)}/_apis/wit/workitems/${quote(work_item_type)}?api-version=7.1"
        headers = self._get_headers(content_type="application/json-patch+json")

        full_ops = base_ops + custom_ops
        resp = requests.post(url, headers=headers, data=json.dumps(full_ops), timeout=20)

        if resp.status_code in (200, 201):
            return self._parse_work_item_response(resp.json(), project, warnings=[])

        if custom_ops and resp.status_code == 400:
            custom_ops_str = [{"op": op["op"], "path": op["path"], "value": str(op["value"])} for op in custom_ops]
            resp_retry1 = requests.post(url, headers=headers, data=json.dumps(base_ops + custom_ops_str), timeout=20)
            if resp_retry1.status_code in (200, 201):
                return self._parse_work_item_response(resp_retry1.json(), project, warnings=[])

            if extra_details_in_desc:
                for op in base_ops:
                    if op["path"] == "/fields/System.Description":
                        op["value"] = description_html + extra_details_in_desc
            resp_fallback = requests.post(url, headers=headers, data=json.dumps(base_ops), timeout=20)
            if resp_fallback.status_code in (200, 201):
                warn_msg = "Nota: Alguns campos personalizados não existem neste tipo de item e foram incluídos na Descrição."
                return self._parse_work_item_response(resp_fallback.json(), project, warnings=[warn_msg])

        err_msg = f"Erro HTTP {resp.status_code}"
        try:
            err_json = resp.json()
            if "message" in err_json:
                err_msg = err_json["message"]
        except Exception:
            err_msg = resp.text[:300]

        raise Exception(err_msg)

    # -------------------------------------------------------------------------
    # DASHBOARD, QUERIES & WORK ITEM EDITING
    # -------------------------------------------------------------------------
    def get_project_queries(self, project: str):
        """Return list of all saved queries (Shared Queries & My Queries) in a project."""
        url = f"{self.base_url}/{quote(project.strip())}/_apis/wit/queries?$depth=2&$expand=wiql&api-version=7.1"
        queries = []
        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=12)
            if resp.status_code == 200:
                folders = resp.json().get("value", [])
                for folder in folders:
                    folder_name = folder.get("name", "")
                    if folder.get("isFolder") and "children" in folder:
                        for child in folder["children"]:
                            if not child.get("isFolder") and child.get("wiql"):
                                queries.append({
                                    "id": child["id"],
                                    "name": child["name"],
                                    "folder": folder_name,
                                    "path": child.get("path", child["name"])
                                })
                    elif not folder.get("isFolder") and folder.get("wiql"):
                        queries.append({
                            "id": folder["id"],
                            "name": folder["name"],
                            "folder": "",
                            "path": folder.get("path", folder["name"])
                        })
        except Exception:
            pass
        return queries

    def get_work_items_by_ids(self, project: str, ids: list):
        """Fetch full work item details for a batch of IDs (preserving order)."""
        if not ids:
            return []
        batch_ids = [str(i) for i in ids[:200]]
        ids_param = ",".join(batch_ids)
        url = f"{self.base_url}/{quote(project.strip())}/_apis/wit/workitems?ids={ids_param}&api-version=7.1"
        resp = requests.get(url, headers=self._get_headers(), timeout=15)
        if resp.status_code != 200:
            return []

        raw_items = resp.json().get("value", [])
        by_id = {}
        for item in raw_items:
            parsed = self._format_work_item_detail(item, project)
            by_id[parsed["id"]] = parsed

        return [by_id[int(i)] for i in batch_ids if int(i) in by_id]

    def run_query_by_id(self, project: str, query_id: str):
        """Execute a saved query by ID and return its detailed work items."""
        url = f"{self.base_url}/{quote(project.strip())}/_apis/wit/wiql/{quote(query_id.strip())}?api-version=7.1"
        resp = requests.get(url, headers=self._get_headers(), timeout=15)
        if resp.status_code != 200:
            raise Exception(f"Erro ao executar query (HTTP {resp.status_code})")
        data = resp.json()
        work_items_refs = data.get("workItems", [])
        if not work_items_refs and "workItemRelations" in data:
            work_items_refs = [rel["target"] for rel in data["workItemRelations"] if "target" in rel]
        ids = [w["id"] for w in work_items_refs if "id" in w]
        return self.get_work_items_by_ids(project, ids)

    def run_wiql(self, project: str, wiql_str: str):
        """Execute an ad-hoc WIQL query and return its detailed work items."""
        url = f"{self.base_url}/{quote(project.strip())}/_apis/wit/wiql?api-version=7.1"
        resp = requests.post(url, headers=self._get_headers(), data=json.dumps({"query": wiql_str}), timeout=15)
        if resp.status_code != 200:
            return []
        data = resp.json()
        work_items_refs = data.get("workItems", [])
        ids = [w["id"] for w in work_items_refs if "id" in w]
        return self.get_work_items_by_ids(project, ids)

    def get_overview_dashboard_data(self, project: str = "One_FrontEnd", dashboard_name: str = "📋 Equipe de Desenvolvimento - Overview"):
        """
        Fetch blocks/queries for the selected Dashboard in parallel.
        """
        from concurrent.futures import ThreadPoolExecutor

        all_queries = self.get_project_queries(project)
        query_by_id = {q["id"]: q for q in all_queries}

        ordered_specs = []
        seen_ids = set()

        if dashboard_name in self.DASHBOARDS_MAP and project.strip().lower() == "one_frontend":
            # Specific dashboard selected (e.g. Equipe de Desenvolvimento - Overview)
            for p_spec in self.DASHBOARDS_MAP[dashboard_name]:
                qid = p_spec["query_id"]
                if qid in query_by_id:
                    ordered_specs.append({
                        "query_id": qid,
                        "title": p_spec["title"],
                        "tag": p_spec.get("tag", "")
                    })
                    seen_ids.add(qid)
        else:
            # "Todos os Blocos" or another project
            for p_spec in self.OVERVIEW_PRIORITY:
                qid = p_spec["query_id"]
                if qid in query_by_id and qid not in seen_ids:
                    ordered_specs.append({
                        "query_id": qid,
                        "title": p_spec["title"],
                        "tag": p_spec.get("tag", "")
                    })
                    seen_ids.add(qid)

            for q in all_queries:
                qid = q["id"]
                if qid not in seen_ids:
                    ordered_specs.append({
                        "query_id": qid,
                        "title": q["name"],
                        "tag": ""
                    })
                    seen_ids.add(qid)

        def fetch_one(spec):
            qid = spec["query_id"]
            items = []
            try:
                items = self.run_query_by_id(project, qid)
            except Exception:
                items = []
            query_url = f"{self.base_url}/{quote(project.strip())}/_queries/query/{qid}/"
            return {
                "key": qid[:8],
                "title": spec["title"],
                "tag": spec["tag"],
                "query_id": qid,
                "query_url": query_url,
                "items": items
            }

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(fetch_one, ordered_specs))

        return results

    def get_work_item(self, project: str, work_item_id: int):
        """Fetch a single work item with full fields and relations."""
        url = f"{self.base_url}/{quote(project.strip())}/_apis/wit/workitems/{int(work_item_id)}?$expand=all&api-version=7.1"
        resp = requests.get(url, headers=self._get_headers(), timeout=15)
        if resp.status_code != 200:
            raise Exception(f"Não foi possível carregar o card #{work_item_id} (HTTP {resp.status_code})")
        return self._format_work_item_detail(resp.json(), project)

    def update_work_item(
        self,
        project: str,
        work_item_id: int,
        title: str = None,
        state: str = None,
        assigned_to: str = None,
        tags: str = None,
        urgency: str = None,
        reported_by: str = None,
        description_html: str = None,
        comment: str = None,
        attachment_paths: list = None
    ):
        """Update fields, add comments, or attach files to an existing Work Item."""
        project = project.strip()
        ops = []

        if title is not None:
            ops.append({"op": "add", "path": "/fields/System.Title", "value": title.strip()})

        if state is not None and state.strip():
            ops.append({"op": "add", "path": "/fields/System.State", "value": state.strip()})

        if assigned_to is not None:
            ops.append({"op": "add", "path": "/fields/System.AssignedTo", "value": assigned_to.strip()})

        if tags is not None:
            ops.append({"op": "add", "path": "/fields/System.Tags", "value": tags.strip()})

        if description_html is not None:
            ops.append({"op": "add", "path": "/fields/System.Description", "value": description_html})

        if comment and comment.strip():
            comment_html = plain_text_to_html(comment.strip())
            ops.append({"op": "add", "path": "/fields/System.History", "value": comment_html})

        if urgency is not None and str(urgency).strip():
            urg_str = str(urgency).strip()
            urg_val = int(urg_str) if urg_str.isdigit() else urg_str
            ops.append({"op": "add", "path": "/fields/MMToolsProcess.Urgency", "value": urg_val})

        if reported_by is not None:
            ops.append({"op": "add", "path": "/fields/MMToolsProcess.ReportedBy", "value": reported_by.strip()})

        if attachment_paths:
            for path in attachment_paths:
                if os.path.exists(path):
                    att_name = os.path.basename(path)
                    att_url = self.upload_attachment(project, path, att_name)
                    if att_url:
                        ops.append({
                            "op": "add",
                            "path": "/relations/-",
                            "value": {
                                "rel": "AttachedFile",
                                "url": att_url,
                                "attributes": {"comment": f"Anexo adicionado na edição ({att_name})"}
                            }
                        })

        if not ops:
            return self.get_work_item(project, work_item_id)

        url = f"{self.base_url}/{quote(project)}/_apis/wit/workitems/{int(work_item_id)}?api-version=7.1"
        headers = self._get_headers(content_type="application/json-patch+json")
        resp = requests.patch(url, headers=headers, data=json.dumps(ops), timeout=20)

        if resp.status_code in (200, 201):
            return self._format_work_item_detail(resp.json(), project)

        # Fallback if MMToolsProcess custom fields don't exist on another project template
        if resp.status_code == 400:
            ops_fallback = [op for op in ops if not op["path"].startswith("/fields/MMToolsProcess.")]
            resp2 = requests.patch(url, headers=headers, data=json.dumps(ops_fallback), timeout=20)
            if resp2.status_code in (200, 201):
                return self._format_work_item_detail(resp2.json(), project)

        err_msg = f"Erro HTTP {resp.status_code}"
        try:
            err_json = resp.json()
            if "message" in err_json:
                err_msg = err_json["message"]
        except Exception:
            err_msg = resp.text[:300]
        raise Exception(err_msg)

    def _format_work_item_detail(self, data: dict, project: str):
        wi_id = data.get("id")
        fields = data.get("fields", {})
        title = fields.get("System.Title", "")
        wi_type = fields.get("System.WorkItemType", "Spike")
        state = fields.get("System.State", "New")
        tags = fields.get("System.Tags", "")
        team_project = fields.get("System.TeamProject", project)

        assigned_obj = fields.get("System.AssignedTo", "")
        if isinstance(assigned_obj, dict):
            assigned_display = assigned_obj.get("displayName", "")
            assigned_unique = assigned_obj.get("uniqueName", assigned_display)
        else:
            assigned_display = str(assigned_obj or "")
            assigned_unique = assigned_display

        description_html = fields.get("System.Description", "") or ""
        description_plain = html_to_plain_text(description_html)

        urgency = fields.get("MMToolsProcess.Urgency", fields.get("Custom.Urgency", fields.get("Microsoft.VSTS.Common.Priority", "")))
        reported_by = fields.get("MMToolsProcess.ReportedBy", fields.get("Custom.ReportedBy", ""))
        noticed_at = fields.get("MMToolsProcess.NoticedAt", fields.get("Custom.NoticedAt", ""))

        web_url = data.get("_links", {}).get("html", {}).get("href")
        if not web_url:
            web_url = f"{self.base_url}/{quote(team_project)}/_workitems/edit/{wi_id}"

        relations = data.get("relations", []) or []
        attachments_count = sum(1 for r in relations if r.get("rel") == "AttachedFile")

        return {
            "id": wi_id,
            "title": title,
            "type": wi_type,
            "state": state,
            "assigned_to": assigned_display,
            "assigned_unique": assigned_unique,
            "tags": tags,
            "urgency": str(urgency) if urgency is not None else "",
            "reported_by": str(reported_by or ""),
            "noticed_at": str(noticed_at or ""),
            "description_html": description_html,
            "description_plain": description_plain,
            "project": team_project,
            "url": web_url,
            "attachments_count": attachments_count
        }

    def _parse_work_item_response(self, data: dict, project: str, warnings: list):
        detail = self._format_work_item_detail(data, project)
        detail["created_at"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        detail["warnings"] = warnings
        return detail
