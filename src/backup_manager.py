"""
Enhanced Cognee - Backup Manager

Comprehensive backup system for Enhanced Cognee stack:
- PostgreSQL (pg_dump)
- Qdrant (snapshot API)
- Neo4j (backup API)
- Redis (RDB snapshot)

Features:
- On-demand backups
- Scheduled backups (daily, weekly, monthly)
- Backup rotation (daily, weekly, monthly retention)
- Backup compression
- Backup verification
- Backup metadata tracking

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import os
import sys
import json
import gzip
import shutil
import hashlib
import logging
import subprocess
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import uuid

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.lite_mode.sqlite_manager import SQLiteManager

logger = logging.getLogger(__name__)


class BackupManager:
    """
    Comprehensive backup manager for Enhanced Cognee databases.

    Supports backing up:
    - PostgreSQL (via pg_dump)
    - Qdrant (via snapshot API)
    - Neo4j (via backup API)
    - Redis (via RDB snapshot)
    """

    def __init__(
        self,
        backup_dir: str = "backups",
        metadata_db: str = "backups/metadata.db"
    ):
        """
        Initialize backup manager.

        Args:
            backup_dir: Base directory for backups
            metadata_db: Path to metadata database
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Initialize metadata database
        self.metadata_db = SQLiteManager(metadata_db)

        # Create backup subdirectories
        (self.backup_dir / "postgresql").mkdir(exist_ok=True)
        (self.backup_dir / "qdrant").mkdir(exist_ok=True)
        (self.backup_dir / "neo4j").mkdir(exist_ok=True)
        (self.backup_dir / "redis").mkdir(exist_ok=True)
        (self.backup_dir / "full").mkdir(exist_ok=True)

        # Load environment configuration
        self.config = self._load_config()

        logger.info("Backup Manager initialized")

    def _load_config(self) -> Dict[str, Any]:
        """Load database configuration from environment."""
        return {
            "postgresql": {
                "host": os.getenv("POSTGRES_HOST", "localhost"),
                "port": os.getenv("POSTGRES_PORT", "25432"),
                "database": os.getenv("POSTGRES_DB", "cognee_db"),
                "user": os.getenv("POSTGRES_USER", "cognee_user"),
                "password": os.getenv("POSTGRES_PASSWORD", "cognee_password")
            },
            "qdrant": {
                "host": os.getenv("QDRANT_HOST", "localhost"),
                "port": os.getenv("QDRANT_PORT", "26333"),
                "api_key": os.getenv("QDRANT_API_KEY", "")
            },
            "neo4j": {
                "uri": os.getenv("NEO4J_URI", "bolt://localhost:27687"),
                "user": os.getenv("NEO4J_USER", "neo4j"),
                "password": os.getenv("NEO4J_PASSWORD", "cognee_password")
            },
            "redis": {
                "host": os.getenv("REDIS_HOST", "localhost"),
                "port": os.getenv("REDIS_PORT", "26379"),
                "password": os.getenv("REDIS_PASSWORD", "")
            }
        }

    def create_backup(
        self,
        backup_type: str = "manual",
        databases: Optional[List[str]] = None,
        compress: bool = True,
        description: str = ""
    ) -> str:
        """
        Create a backup of specified databases.

        Args:
            backup_type: Type of backup ('manual', 'daily', 'weekly', 'monthly')
            databases: List of databases to backup (default: all)
            compress: Whether to compress backups
            description: Optional description

        Returns:
            Backup ID
        """
        backup_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / backup_type / f"backup_{timestamp}_{backup_id}"

        try:
            backup_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Creating backup: {backup_id}")

            # Default to all databases if not specified
            if databases is None:
                databases = ["postgresql", "qdrant", "neo4j", "redis"]

            backup_results = {}
            errors = []

            # Backup each database
            for db in databases:
                try:
                    result = self._backup_database(db, backup_path, compress)
                    backup_results[db] = result
                    logger.info(f"Backed up {db}: {result['file_path']}")
                except Exception as e:
                    logger.error(f"Failed to backup {db}: {e}")
                    errors.append(f"{db}: {str(e)}")
                    backup_results[db] = {"status": "failed", "error": str(e)}

            # Calculate total size and checksum
            total_size = sum(
                r.get('file_size', 0) for r in backup_results.values() if r.get('status') == 'success'
            )

            checksum = self._calculate_backup_checksum(backup_path)

            # Store metadata
            metadata = {
                "backup_id": backup_id,
                "backup_type": backup_type,
                "created_at": datetime.now().isoformat(),
                "backup_path": str(backup_path),
                "databases_backed_up": list(databases),
                "backup_results": backup_results,
                "total_size_bytes": total_size,
                "compressed": compress,
                "checksum": checksum,
                "description": description,
                "status": "completed" if not errors else "partial"
            }

            self._store_backup_metadata(metadata)

            if errors:
                logger.warning(f"Backup completed with errors: {errors}")

            logger.info(f"Backup created: {backup_id} ({total_size:,} bytes)")
            return backup_id

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            raise

    def _backup_database(
        self,
        database: str,
        backup_path: Path,
        compress: bool
    ) -> Dict[str, Any]:
        """
        Backup a specific database.

        Args:
            database: Database name ('postgresql', 'qdrant', 'neo4j', 'redis')
            backup_path: Backup directory path
            compress: Whether to compress

        Returns:
            Backup result dictionary
        """
        if database == "postgresql":
            return self._backup_postgresql(backup_path, compress)
        elif database == "qdrant":
            return self._backup_qdrant(backup_path, compress)
        elif database == "neo4j":
            return self._backup_neo4j(backup_path, compress)
        elif database == "redis":
            return self._backup_redis(backup_path, compress)
        else:
            raise ValueError(f"Unknown database: {database}")

    def _backup_postgresql(self, backup_path: Path, compress: bool) -> Dict[str, Any]:
        """Backup PostgreSQL using pg_dump."""
        config = self.config["postgresql"]
        filename = f"postgresql_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        filepath = backup_path / filename

        if compress:
            filename += ".gz"
            filepath = backup_path / filename

        # Build pg_dump command
        cmd = [
            "pg_dump",
            f"--host={config['host']}",
            f"--port={config['port']}",
            f"--username={config['user']}",
            f"--dbname={config['database']}",
            "--no-password",
            "--format=plain",
            "--no-owner",
            "--no-acl"
        ]

        env = os.environ.copy()
        env["PGPASSWORD"] = config["password"]

        try:
            # Execute pg_dump
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                raise RuntimeError(f"pg_dump failed: {result.stderr}")

            # Write output (compress if needed)
            output = result.stdout.encode('utf-8')

            if compress:
                with gzip.open(filepath, 'wb') as f:
                    f.write(output)
            else:
                with open(filepath, 'wb') as f:
                    f.write(output)

            file_size = filepath.stat().st_size

            return {
                "status": "success",
                "database": "postgresql",
                "file_path": str(filepath),
                "file_size": file_size,
                "compressed": compress,
                "command": " ".join(cmd)
            }

        except subprocess.TimeoutExpired:
            raise RuntimeError("pg_dump timeout after 5 minutes")
        except Exception as e:
            raise RuntimeError(f"PostgreSQL backup failed: {e}")

    def _backup_qdrant(self, backup_path: Path, compress: bool) -> Dict[str, Any]:
        """Backup Qdrant using snapshot API."""
        config = self.config["qdrant"]
        filename = f"qdrant_{datetime.now().strftime('%Y%m%d_%H%M%S')}.snapshot"
        filepath = backup_path / filename

        try:
            # Qdrant snapshot API
            import requests

            url = f"http://{config['host']}:{config['port']}/collections/ALL/snapshots"
            headers = {}

            if config.get("api_key"):
                headers["api-key"] = config["api_key"]

            # Create snapshot
            response = requests.post(url, headers=headers, timeout=60)

            if response.status_code != 200:
                raise RuntimeError(f"Qdrant snapshot API failed: {response.text}")

            # Download snapshot
            snapshot_info = response.json()
            snapshot_url = snapshot_info.get("result", "")

            if not snapshot_url:
                raise RuntimeError("No snapshot URL returned")

            # Download snapshot file
            snapshot_response = requests.get(snapshot_url, timeout=300)
            snapshot_response.raise_for_status()

            # Write snapshot (compress if needed)
            output = snapshot_response.content

            if compress:
                filename += ".gz"
                filepath = backup_path / filename
                with gzip.open(filepath, 'wb') as f:
                    f.write(output)
            else:
                with open(filepath, 'wb') as f:
                    f.write(output)

            file_size = filepath.stat().st_size

            return {
                "status": "success",
                "database": "qdrant",
                "file_path": str(filepath),
                "file_size": file_size,
                "compressed": compress,
                "snapshot_url": snapshot_url
            }

        except Exception as e:
            raise RuntimeError(f"Qdrant backup failed: {e}")

    def _backup_neo4j(self, backup_path: Path, compress: bool) -> Dict[str, Any]:
        """Backup Neo4j using backup API."""
        config = self.config["neo4j"]
        filename = f"neo4j_{datetime.now().strftime('%Y%m%d_%H%M%S')}.backup"
        filepath = backup_path / filename

        try:
            # For Docker Neo4j, use docker exec
            docker_cmd = [
                "docker", "exec", "neo4j-enhanced",
                "neo4j-admin", "backup",
                "--backup-path=/backups",
                "--to-path=/data/neo4j_backup"
            ]

            try:
                result = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=300)

                if result.returncode == 0:
                    # Copy backup from container
                    subprocess.run([
                        "docker", "cp",
                        "neo4j-enhanced:/data/neo4j_backup",
                        str(filepath)
                    ], timeout=60)

                    file_size = filepath.stat().st_size

                    return {
                        "status": "success",
                        "database": "neo4j",
                        "file_path": str(filepath),
                        "file_size": file_size,
                        "compressed": False,
                        "method": "docker"
                    }

            except Exception as e:
                logger.warning(f"Docker backup failed, trying Cypher export: {e}")

            # Fallback: Cypher query to export data
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(
                config["uri"],
                auth=(config["user"], config["password"])
            )

            with driver.session() as session:
                # Export all nodes and relationships
                result = session.run("MATCH (n) RETURN n")

                data = []
                for record in result:
                    node = record["n"]
                    data.append({
                        "id": element_id(node),
                        "labels": list(node.labels),
                        "properties": dict(node)
                    })

            driver.close()

            # Write to JSON
            output = json.dumps(data, indent=2).encode('utf-8')

            if compress:
                filename += ".gz"
                filepath = backup_path / filename
                with gzip.open(filepath, 'wb') as f:
                    f.write(output)
            else:
                with open(filepath, 'wb') as f:
                    f.write(output)

            file_size = filepath.stat().st_size

            return {
                "status": "success",
                "database": "neo4j",
                "file_path": str(filepath),
                "file_size": file_size,
                "compressed": compress,
                "method": "cypher_export"
            }

        except Exception as e:
            raise RuntimeError(f"Neo4j backup failed: {e}")

    def _backup_redis(self, backup_path: Path, compress: bool) -> Dict[str, Any]:
        """Backup Redis using RDB snapshot."""
        config = self.config["redis"]
        filename = f"redis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.rdb"
        filepath = backup_path / filename

        try:
            # Use docker exec for Redis in Docker
            docker_cmd = [
                "docker", "exec", "redis-enhanced",
                "redis-cli",
                "-a", config.get("password", ""),
                "BGSAVE"
            ]

            result = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                raise RuntimeError(f"Redis BGSAVE failed: {result.stderr}")

            # Wait for BGSAVE to complete
            import time
            time.sleep(5)

            # Copy RDB file from container
            copy_cmd = [
                "docker", "cp",
                "redis-enhanced:/data/dump.rdb",
                str(filepath)
            ]

            result = subprocess.run(copy_cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                raise RuntimeError(f"Failed to copy RDB file: {result.stderr}")

            file_size = filepath.stat().st_size

            # Compress if needed
            if compress:
                compressed_filepath = backup_path / f"{filename}.gz"

                with open(filepath, 'rb') as f_in:
                    with gzip.open(compressed_filepath, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)

                os.remove(filepath)
                filepath = compressed_filepath
                file_size = filepath.stat().st_size

            return {
                "status": "success",
                "database": "redis",
                "file_path": str(filepath),
                "file_size": file_size,
                "compressed": compress
            }

        except Exception as e:
            raise RuntimeError(f"Redis backup failed: {e}")

    def _calculate_backup_checksum(self, backup_path: Path) -> str:
        """Calculate SHA256 checksum of backup directory."""
        sha256_hash = hashlib.sha256()

        for root, dirs, files in os.walk(backup_path):
            for file in files:
                filepath = os.path.join(root, file)
                with open(filepath, "rb") as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()

    def _store_backup_metadata(self, metadata: Dict[str, Any]):
        """Store backup metadata in database."""
        self.metadata_db.add_document(
            data_id=metadata["backup_id"],
            data_text=json.dumps(metadata, indent=2),
            data_type="backup_metadata",
            metadata=metadata,
            user_id="backup_system",
            agent_id="backup_manager"
        )

    def list_backups(
        self,
        backup_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List all backups.

        Args:
            backup_type: Filter by backup type (optional)
            limit: Maximum results

        Returns:
            List of backup metadata
        """
        query = "backup_metadata"

        if backup_type:
            query = f"{query} {backup_type}"

        # Search metadata database
        results = self.metadata_db.search_documents(query, user_id="backup_system", limit=limit)

        backups = []
        for result in results:
            metadata = json.loads(result['data_text'])
            backups.append(metadata)

        return sorted(backups, key=lambda x: x['created_at'], reverse=True)[:limit]

    def get_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """
        Get backup metadata by ID.

        Args:
            backup_id: Backup ID

        Returns:
            Backup metadata or None
        """
        # Search metadata database
        results = self.metadata_db.search_documents(backup_id, user_id="backup_system", limit=1)

        if results:
            return json.loads(results[0]['data_text'])

        return None

    def delete_backup(self, backup_id: str) -> bool:
        """
        Delete a backup.

        Args:
            backup_id: Backup ID

        Returns:
            True if deleted, False otherwise
        """
        backup = self.get_backup(backup_id)

        if not backup:
            logger.warning(f"Backup not found: {backup_id}")
            return False

        try:
            # Delete backup files
            backup_path = Path(backup['backup_path'])
            if backup_path.exists():
                shutil.rmtree(backup_path)

            # Delete from metadata
            self.metadata_db.delete_document(backup_id)

            logger.info(f"Backup deleted: {backup_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete backup: {e}")
            return False

    def rotate_backups(self):
        """
        Rotate old backups based on retention policy.

        Retention:
        - Daily backups: Keep 7 days
        - Weekly backups: Keep 4 weeks
        - Monthly backups: Keep 12 months
        - Manual backups: Keep forever
        """
        logger.info("Starting backup rotation...")

        now = datetime.now()

        # Daily backups - keep 7 days
        daily_cutoff = now - timedelta(days=7)
        self._rotate_backup_type("daily", daily_cutoff)

        # Weekly backups - keep 4 weeks
        weekly_cutoff = now - timedelta(weeks=4)
        self._rotate_backup_type("weekly", weekly_cutoff)

        # Monthly backups - keep 12 months
        monthly_cutoff = now - timedelta(days=365)
        self._rotate_backup_type("monthly", monthly_cutoff)

        logger.info("Backup rotation complete")

    def _rotate_backup_type(self, backup_type: str, cutoff: datetime):
        """Rotate backups of a specific type."""
        backups = self.list_backups(backup_type=backup_type, limit=1000)

        for backup in backups:
            created_at = datetime.fromisoformat(backup['created_at'])

            if created_at < cutoff:
                logger.info(f"Deleting old {backup_type} backup: {backup['backup_id']}")
                self.delete_backup(backup['backup_id'])


if __name__ == "__main__":
    # Test backup manager
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    manager = BackupManager()

    # Create a test backup
    backup_id = manager.create_backup(
        backup_type="manual",
        databases=["postgresql"],  # Just PostgreSQL for testing
        compress=True,
        description="Test backup"
    )

    print(f"[OK] Backup created: {backup_id}")

    # List backups
    backups = manager.list_backups()
    print(f"[INFO] Total backups: {len(backups)}")
