import io
import re
from pathlib import Path
import pandas as pd
import numpy as np

CONTAINER_COLUMNS = ["container_id","size","weight","destination","destination_order","priority","hazardous","refrigerated"]
SLOT_COLUMNS = ["slot_id","bay","row","tier","size","max_weight","reefer_capable","hazardous_allowed"]

ALIASES = {
 "container_id": ["container_id","containerid","container_no","container_number","container","cntr_id","cntr_no","id"],
 "weight": ["weight","container_weight","gross_weight","grossweight","weight_kg","mass","cargo_weight"],
 "destination": ["destination","destination_port","dest","discharge_port","port_of_discharge","pod","delivery_port"],
 "destination_order": ["destination_order","port_order","discharge_order","stop_order","sequence","port_sequence"],
 "priority": ["priority","priority_level","importance","rank"],
 "hazardous": ["hazardous","hazard","dangerous","dangerous_goods","dg","hazmat","is_hazardous"],
 "refrigerated": ["refrigerated","reefer","is_reefer","refrigeration","temperature_controlled","cold_storage"],
 "slot_id": ["slot_id","slotid","slot_no","slot_number","position_id","position","cell_id"],
 "bay": ["bay","bay_no","bay_number","bayid"],
 "row": ["row","row_no","row_number","rowid"],
 "tier": ["tier","tier_no","tier_number","level","deck_level"],
 "max_weight": ["max_weight","maximum_weight","weight_limit","capacity","max_load","slot_capacity"],
 "reefer_capable": ["reefer_capable","reefer_allowed","reefer_support","power_available","refrigerated_allowed"],
 "hazardous_allowed": ["hazardous_allowed","hazard_allowed","dangerous_allowed","dg_allowed","hazmat_allowed"],
 "size": ["size","container_size","slot_size","length","length_ft","size_ft","teu_size"],
}

def clean_name(value):
    s = str(value).strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s

def _alias_map():
    out = {}
    for canonical, aliases in ALIASES.items():
        for a in aliases:
            out[clean_name(a)] = canonical
    return out
ALIAS_MAP = _alias_map()

def rename_columns(df):
    used=set(); mapping={}
    for col in df.columns:
        key=clean_name(col); canonical=ALIAS_MAP.get(key)
        if canonical and canonical not in used:
            mapping[col]=canonical; used.add(canonical)
        else:
            mapping[col]=key or f"column_{len(mapping)+1}"
    return df.rename(columns=mapping)

def parse_bool(value, default=False):
    if pd.isna(value): return default
    if isinstance(value,(bool,np.bool_)): return bool(value)
    if isinstance(value,(int,float,np.integer,np.floating)): return float(value)!=0
    s=str(value).strip().lower()
    if s in {"true","t","yes","y","1","on","allowed","available","reefer","hazardous"}: return True
    if s in {"false","f","no","n","0","off","not allowed","unavailable","none","non-hazardous","non hazardous"}: return False
    return default

def parse_size(value, default=20):
    if pd.isna(value): return default
    s=str(value).strip().lower().replace("feet","ft").replace("foot","ft")
    nums=re.findall(r"\d+(?:\.\d+)?",s)
    if nums:
        n=float(nums[0])
        if n in (1,2): return 20 if n==1 else 40
        return 40 if n>=35 else 20
    if "forty" in s: return 40
    if "twenty" in s: return 20
    return default

def num_series(series, default, minimum=None):
    x=pd.to_numeric(series,errors="coerce")
    if x.notna().any():
        fill=float(x[x.notna()].median())
    else: fill=float(default)
    x=x.fillna(fill)
    if minimum is not None: x=x.clip(lower=minimum)
    return x

def read_csv_safely(raw: bytes):
    errors=[]
    for enc in ("utf-8-sig","utf-8","latin-1"):
        for sep in (None,",",";","\t","|"):
            try:
                df=pd.read_csv(io.BytesIO(raw),encoding=enc,sep=sep,engine="python")
                if len(df.columns)>=2 and len(df)>0:
                    return df, errors
            except Exception as e: errors.append(str(e))
    raise ValueError("CSV could not be parsed. Ensure it contains a header row and at least two columns.")

def classify_dataframe(df, filename=""):
    cols=set(rename_columns(df).columns)
    c=sum(k in cols for k in ["container_id","weight","destination","hazardous","refrigerated"])
    s=sum(k in cols for k in ["slot_id","bay","row","tier","max_weight","reefer_capable","hazardous_allowed"])
    name=clean_name(Path(filename).stem)
    if any(k in name for k in ["slot","vessel","position","bay"]): s+=2
    if any(k in name for k in ["container","cargo","manifest"]): c+=2
    if s>=3 and s>c: return "slots", c, s
    if c>=2 and c>=s: return "containers", c, s
    # Position triplet is a strong slot signal; weight+destination is a strong container signal.
    if {"bay","row","tier"}.issubset(cols): return "slots",c,s
    if "weight" in cols and "destination" in cols: return "containers",c,s
    return "unknown",c,s

def normalize_containers(df, source="upload.csv"):
    df=rename_columns(df.copy()).dropna(how="all").reset_index(drop=True)
    warnings=[]
    n=len(df)
    if not n: raise ValueError(f"{source}: no data rows found.")
    if "container_id" not in df: df["container_id"]=[f"C-{i+1:05d}" for i in range(n)]; warnings.append("container_id missing: generated IDs.")
    df["container_id"]=df["container_id"].astype(str).str.strip().replace({"":"UNKNOWN","nan":"UNKNOWN","None":"UNKNOWN"})
    if "size" not in df: df["size"]=20; warnings.append("size missing: defaulted to 20 ft.")
    df["size"]=df["size"].map(parse_size).astype(int)
    if "weight" not in df: df["weight"]=15000; warnings.append("weight missing: defaulted to 15,000 kg.")
    df["weight"]=num_series(df["weight"],15000,0).round(2)
    if "destination" not in df: df["destination"]="Unknown Port"; warnings.append("destination missing: set to Unknown Port.")
    df["destination"]=df["destination"].fillna("Unknown Port").astype(str).str.strip().replace({"":"Unknown Port","nan":"Unknown Port"})
    if "destination_order" not in df:
        order={v:i+1 for i,v in enumerate(pd.unique(df["destination"]))}; df["destination_order"]=df["destination"].map(order); warnings.append("destination_order missing: derived from destination appearance order.")
    df["destination_order"]=num_series(df["destination_order"],1,1).round().astype(int)
    if "priority" not in df: df["priority"]=2; warnings.append("priority missing: defaulted to 2.")
    df["priority"]=num_series(df["priority"],2,1).clip(upper=3).round().astype(int)
    for col in ["hazardous","refrigerated"]:
        if col not in df: df[col]=False; warnings.append(f"{col} missing: defaulted to false.")
        df[col]=df[col].map(parse_bool).astype(bool)
    return df[CONTAINER_COLUMNS], warnings

def normalize_slots(df, source="upload.csv"):
    df=rename_columns(df.copy()).dropna(how="all").reset_index(drop=True)
    warnings=[]; n=len(df)
    if not n: raise ValueError(f"{source}: no data rows found.")
    # Position defaults make incomplete slot sheets usable without inventing random positions.
    if "bay" not in df: df["bay"]=[i//10+1 for i in range(n)]; warnings.append("bay missing: generated sequential bays.")
    if "row" not in df: df["row"]=[(i//2)%5+1 for i in range(n)]; warnings.append("row missing: generated rows 1-5.")
    if "tier" not in df: df["tier"]=[i%2+1 for i in range(n)]; warnings.append("tier missing: generated tiers 1-2.")
    for col in ["bay","row","tier"]: df[col]=num_series(df[col],1,1).round().astype(int)
    if "slot_id" not in df: df["slot_id"]=[f"B{b:02d}-R{r:02d}-T{t:02d}" for b,r,t in zip(df.bay,df.row,df.tier)]; warnings.append("slot_id missing: generated from bay-row-tier.")
    df["slot_id"]=df["slot_id"].astype(str).str.strip()
    if "size" not in df: df["size"]=20; warnings.append("size missing: defaulted to 20 ft.")
    df["size"]=df["size"].map(parse_size).astype(int)
    if "max_weight" not in df: df["max_weight"]=df["size"].map({20:30000,40:35000}); warnings.append("max_weight missing: defaulted by slot size.")
    df["max_weight"]=num_series(df["max_weight"],30000,0).round(2)
    for col,default in [("reefer_capable",False),("hazardous_allowed",True)]:
        if col not in df: df[col]=default; warnings.append(f"{col} missing: defaulted to {str(default).lower()}.")
        df[col]=df[col].map(lambda x: parse_bool(x,default)).astype(bool)
    return df[SLOT_COLUMNS], warnings

def make_unique(series,prefix):
    seen={}; out=[]
    for i,v in enumerate(series.astype(str)):
        base=v.strip() or f"{prefix}{i+1:05d}"; count=seen.get(base,0); seen[base]=count+1
        out.append(base if count==0 else f"{base}-{count+1}")
    return out

def ingest_files(items):
    containers=[]; slots=[]; reports=[]; all_warnings=[]
    for filename,raw in items:
        df,_=read_csv_safely(raw); kind,cscore,sscore=classify_dataframe(df,filename)
        report={"file":filename,"rows":len(df),"original_columns":[str(c) for c in df.columns],"detected_type":kind,"container_score":cscore,"slot_score":sscore,"warnings":[]}
        if kind=="containers": clean,w=normalize_containers(df,filename); containers.append(clean)
        elif kind=="slots": clean,w=normalize_slots(df,filename); slots.append(clean)
        else:
            raise ValueError(f"{filename}: could not determine whether this is container/cargo data or vessel slot data. Include recognizable fields such as weight + destination for containers, or bay + row + tier / max weight for slots.")
        report["warnings"]=w; all_warnings.extend([f"{filename}: {x}" for x in w]); reports.append(report)
    if not containers: raise ValueError("No container/cargo CSV was detected in the uploaded files.")
    if not slots: raise ValueError("No vessel slot CSV was detected in the uploaded files.")
    c=pd.concat(containers,ignore_index=True); s=pd.concat(slots,ignore_index=True)
    c["container_id"]=make_unique(c["container_id"],"C")
    s["slot_id"]=make_unique(s["slot_id"],"S")
    return c,s,reports,all_warnings
