from pathlib import Path
import subprocess
from uuid import uuid4

from .api_client import (
    api_add_role_to_target,
    api_add_role_to_user,
    api_admin_session,
    api_create_role,
    api_create_target,
    api_create_user,
)
from .conftest import ProcessManager, WarpgateProcess
from .util import wait_port


class Test:
    def test_bad_target(
        self,
        processes: ProcessManager,
        wg_c_ed25519_pubkey: Path,
        shared_wg: WarpgateProcess,
    ):
        ssh_port = processes.start_ssh_server(
            trusted_keys=[wg_c_ed25519_pubkey.read_text()]
        )

        wait_port(ssh_port)

        url = f'https://localhost:{shared_wg.http_port}'
        with api_admin_session(url) as session:
            role = api_create_role(url, session, {"name": f"role-{uuid4()}"})
            user = api_create_user(
                url,
                session,
                {
                    "username": f"user-{uuid4()}",
                    "credentials": [
                        {
                            "kind": "Password",
                            "hash": "123",
                        },
                    ],
                },
            )
            api_add_role_to_user(url, session, user["id"], role["id"])
            ssh_target = api_create_target(
                url,
                session,
                {
                    "name": f"ssh-{uuid4()}",
                    "options": {
                        "kind": "Ssh",
                        "host": "localhost",
                        "port": ssh_port,
                        "username": "root",
                        "auth": {"kind": "PublicKey"},
                    },
                },
            )
            api_add_role_to_target(url, session, ssh_target["id"], role["id"])

        ssh_client = processes.start_ssh_client(
            "-t",
            f"{user['username']}:badtarget@localhost",
            "-p",
            str(shared_wg.ssh_port),
            "-i",
            "/dev/null",
            "-o",
            "PreferredAuthentications=password",
            "echo",
            "hello",
            stderr=subprocess.PIPE,
            password="123",
        )
        assert ssh_client.returncode != 0
        assert b"Permission denied" in ssh_client.stderr.read()
