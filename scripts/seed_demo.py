from pathlib import Path

from dw_warehouse.repository import WarehouseRepository


if __name__ == "__main__":
    repo = WarehouseRepository(Path("data") / "warehouse")
    print(repo.seed_demo())
