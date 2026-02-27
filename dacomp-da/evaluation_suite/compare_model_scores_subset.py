#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path
from statistics import mean


def load(path: Path):
    with open(path, newline='', encoding='utf-8') as f:
        return {r['instance_id']: r for r in csv.DictReader(f)}


def to_float(v):
    try:
        return float(v)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline', required=True)
    ap.add_argument('--candidate', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    b = load(Path(args.baseline))
    c = load(Path(args.candidate))
    ids = sorted(set(b) & set(c))

    rows = []
    wd, rd, ad = [], [], []
    for iid in ids:
        bw = to_float(b[iid].get('weighted_total_score'))
        cw = to_float(c[iid].get('weighted_total_score'))
        br = to_float(b[iid].get('rubrics_total_score'))
        cr = to_float(c[iid].get('rubrics_total_score'))
        ba = to_float(b[iid].get('rubric_accuracy_score_pct'))
        ca = to_float(c[iid].get('rubric_accuracy_score_pct'))

        dw = (cw - bw) if bw is not None and cw is not None else None
        dr = (cr - br) if br is not None and cr is not None else None
        da = (ca - ba) if ba is not None and ca is not None else None

        if dw is not None:
            wd.append(dw)
        if dr is not None:
            rd.append(dr)
        if da is not None:
            ad.append(da)

        rows.append(
            {
                'instance_id': iid,
                'baseline_weighted': bw,
                'candidate_weighted': cw,
                'delta_weighted': dw,
                'delta_rubrics': dr,
                'delta_accuracy_pct': da,
            }
        )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f'cases={len(ids)}')
    print(f'avg_delta_weighted={mean(wd) if wd else "NA"}')
    print(f'avg_delta_rubrics={mean(rd) if rd else "NA"}')
    print(f'avg_delta_accuracy_pct={mean(ad) if ad else "NA"}')
    print(f'improved_weighted={sum(1 for x in wd if x > 0)} worse_weighted={sum(1 for x in wd if x < 0)}')


if __name__ == '__main__':
    main()
