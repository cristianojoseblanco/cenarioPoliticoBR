"""Teste de leitura/escrita DuckDB/Parquet e da conversão de staging."""
from src.config import connect, load_config
from src.ingestion.camara import csv_to_parquet


def test_csv_to_parquet_preserva_texto(tmp_path):
    csv = tmp_path / "votos.csv"
    csv.write_text(
        'idVotacao;deputado_id;voto\n"123-45";"001";"Sim"\n"123-45";"002";"Abstenção"\n"123-45";"003";\n',
        encoding="utf-8",
    )
    out = tmp_path / "out" / "part-0.parquet"
    con = connect(load_config())
    linhas = csv_to_parquet(con, csv, out, ";")
    assert linhas == 3
    rows = con.execute(f"SELECT deputado_id, voto FROM '{out}' ORDER BY 1").fetchall()
    # zeros à esquerda preservados (sem inferência numérica) e vazio mantido distinto
    assert rows[0] == ("001", "Sim")
    assert rows[1][1] == "Abstenção"
    assert rows[2][1] is None
