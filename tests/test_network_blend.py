import pandas as pd
import pytest
from cfb_value_watch.network_blend import compare,FEATURES

def test_blend_never_tunes_on_2025(tmp_path):
    base=[];network=[]
    for year,n in [(2023,1100),(2024,350),(2025,350)]:
        for i in range(n):
            gid=f"{year}-{i}"
            row={"game_id":gid,"season":year,"home_margin":10.0 if i%2 else -10.0}
            row.update({k:float((i+j)%7) for j,k in enumerate(FEATURES)})
            base.append(row)
            if year>=2024:
                # 2024 favors network, 2025 intentionally opposes it.
                pred=(10.0 if i%2 else -10.0)
                if year==2025:pred=-pred
                network.append({"game_id":gid,"season":year,
                                "actual_home_margin":row["home_margin"],
                                "predicted_home_margin":pred})
    b=tmp_path/"baseline.csv";n=tmp_path/"network.csv"
    pd.DataFrame(base).to_csv(b,index=False)
    pd.DataFrame(network).to_csv(n,index=False)
    report=compare(b,n,tmp_path/"out")
    assert report["weight_selected_on"]=="2024"
    assert report["network_weight"]==1.0
    assert report["holdout_year"]==2025
    assert report["blended_holdout_mae"]>report["baseline_holdout_mae"]

def test_blend_rejects_score_mismatch(tmp_path):
    base=[];net=[]
    for year,count in [(2023,1100),(2024,350),(2025,350)]:
        for i in range(count):
            g=f"{year}-{i}"
            row={"game_id":g,"season":year,"home_margin":1}
            row.update({k:float(i%7) for k in FEATURES})
            base.append(row)
            if year>=2024:net.append({"game_id":g,"season":year,
                                      "actual_home_margin":2,
                                      "predicted_home_margin":1})
    a=tmp_path/"a.csv";b=tmp_path/"b.csv"
    pd.DataFrame(base).to_csv(a,index=False)
    pd.DataFrame(net).to_csv(b,index=False)
    with pytest.raises(ValueError,match="mismatch"):
        compare(a,b,tmp_path/"out")
