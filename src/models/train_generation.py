from pathlib import Path
import pickle, pandas as pd
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

DATA = Path("data/processed/features_daily.csv")
OUT  = Path("artifacts/models/generation_xgb.pkl"); OUT.parent.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA)
y  = df["pv_kw"].values
X_df = df.drop(columns=["timestamp","pv_kw","load_kw"])
FEATURES = X_df.columns.tolist()
X = X_df.values

Xtr,Xte,ytr,yte = train_test_split(X,y,test_size=0.2,random_state=42)
model = XGBRegressor(
    n_estimators=500,max_depth=8,learning_rate=0.05,
    subsample=0.9,colsample_bytree=0.9,objective="reg:squarederror",random_state=42)
model.fit(Xtr,ytr)
print(f"[PV] MAE={mean_absolute_error(yte, model.predict(Xte)):.3f} kWh")

with open(OUT,"wb") as f:
    pickle.dump({"model":model,"feat":FEATURES},f)
print(f"[✅] Saved → {OUT}")
