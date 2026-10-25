"""Retirement boundaries and failure recovery using database doubles only."""
import hashlib
import importlib.util
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "integrations/hermes/deployment/retire_launch_postgres_logins.py"
spec = importlib.util.spec_from_file_location("postgres_login_retirement",SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def config(role,field="ENHANCED_MEMORY_DATABASE_URL"):
    return {field:f"postgresql://{role}:invented@127.0.0.1:28434/memory"}


@pytest.fixture
def bindings():
    old = {kind:config("old_"+kind,field) for kind,field in helper.FIELDS.items()}
    current = {kind:config("ec_"+kind+"_012345abcdef",field) for kind,field in helper.FIELDS.items()}
    return old,current,config("operator"),config("backup")


def test_plan_selects_only_old_services_without_altering_configs(bindings):
    old,current,operator,backup = bindings
    assert helper.plan(*bindings) == {"api":"old_api","worker":"old_worker"}
    assert current["api"] == config("ec_api_012345abcdef")
    for protected in (operator,backup,current["api"]):
        collision = dict(old,api=protected)
        with pytest.raises(ValueError):helper.plan(collision,current,operator,backup)


@pytest.mark.parametrize("url",["postgresql://invented:fake@remote.invalid:28434/memory",
    "postgresql://invented:fake@127.0.0.1:5432/memory","postgresql://bad%22role:fake@127.0.0.1:28434/memory"])
def test_external_wrong_port_or_sql_identifier_injection_refused(url):
    with pytest.raises(ValueError):helper.binding(url)


def test_root_and_support_guards_precede_database_access(monkeypatch):
    monkeypatch.setattr(helper.os,"geteuid",lambda:1000)
    with pytest.raises(ValueError,match="fixed_protected_operator_python_required"):helper.main()
    assert hashlib.sha256(SOURCE.with_name("recover_launch_graph_operator.py").read_bytes()).hexdigest() == helper.SHARED_SHA256


class Denied(Exception):
    sqlstate = "28000"


class Service:
    def __init__(self,role):self.role = role
    async def fetchval(self,sql,*args):
        if sql == "SELECT current_user":return self.role
        if "max(version)" in sql:return 3
        if "has_table_privilege" in sql:return False
        raise AssertionError("unexpected service statement")
    async def close(self):pass


class Transaction:
    def __init__(self,admin):self.admin = admin
    async def __aenter__(self):self.before = dict(self.admin.flags)
    async def __aexit__(self,kind,value,tb):
        if kind:self.admin.flags = self.before


class Admin:
    def __init__(self,sessions=0):
        self.flags = {"old_api":True,"old_worker":True}
        self.sessions = sessions
        self.statements = []
    def transaction(self):return Transaction(self)
    async def fetchrow(self,sql,role):
        return dict(oid=100 if role == "old_api" else 101,rolcanlogin=self.flags[role],
                    rolsuper=False,rolcreatedb=False,rolcreaterole=False,rolreplication=False,rolbypassrls=False)
    async def fetchval(self,sql,role):
        if "quote_ident" in sql:return '"'+role+'"'
        if "pg_stat_activity" in sql:return self.sessions
        if "SELECT oid" in sql:return 100 if role == "old_api" else 101
        if "rolcanlogin" in sql:return self.flags[role]
        raise AssertionError("unexpected admin statement")
    async def execute(self,sql):
        self.statements.append(sql)
        _,_,quoted,mode = sql.split()
        self.flags[quoted.strip('"')] = mode == "LOGIN"
    async def close(self):pass


@pytest.mark.asyncio
@pytest.mark.parametrize("failure",[None,"live_old_session","changed_config","network_denial"])
async def test_retirement_verifies_real_denial_categories_and_restores_flags_on_failure(bindings,tmp_path,failure):
    old,current,operator,backup = bindings
    roles = helper.plan(*bindings)
    admin = Admin(sessions=1 if failure == "live_old_session" else 0)
    async def connect(url,**kwargs):
        role = helper.binding(url)[0]
        if role == "operator":return admin
        if role in admin.flags and not admin.flags[role]:
            if failure == "network_denial":raise OSError("invented network failure is not authentication denial")
            raise Denied()
        return Service(role)
    checks = []
    def unchanged():
        checks.append(True)
        if failure == "changed_config" and len(checks) == 2:
            raise ValueError("protected_configuration_changed_concurrently")
    result = {"complete":False}
    await helper.retire(connect,operator,current,old,roles,lambda p,raw:p.write_bytes(raw),tmp_path,result,unchanged)
    if failure is None:
        assert result["complete"] and result["old_service_logins_denied"]
        assert not any(admin.flags.values())
        assert admin.statements == ['ALTER ROLE "old_api" NOLOGIN','ALTER ROLE "old_worker" NOLOGIN']
    else:
        assert not result["complete"] and all(admin.flags.values())
        if failure == "live_old_session":
            assert admin.statements == []
            assert result["reason"] == "old_service_sessions_present_no_termination"
        else:assert result["rollback_login_flags_verified"]
