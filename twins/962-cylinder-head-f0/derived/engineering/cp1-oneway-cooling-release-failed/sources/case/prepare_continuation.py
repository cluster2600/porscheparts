"""HELD finite accepted-grid cooling extension; no solver imports or CSV re-conversion."""
import argparse
from decimal import Decimal, localcontext
import hashlib,json,math
from pathlib import Path
PREP=Path(__file__).resolve().parent
ROOT=PREP.parent.parent.parent
OUTPUT=ROOT/"work/962-engineering/cp1-oneway-cooling-release-inputs-001"
SOURCE=ROOT/"work/962-engineering/cp1-oneway-thermoelastic-transfer-inputs-001"


def need(condition, message):
    if not condition:
        raise ValueError(message)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def table_text(axes, values):
    need(len(axes) in (3, 4), "Only the fixed 3D/4D transfer tables exist")
    need([name for name, _ in axes] == (["X", "Y", "Z"] if len(axes) == 3 else ["X", "Y", "Z", "T"]),
         "X-fastest XYZ[T] axis order required")
    count = 1
    lines = []
    for name, axis in axes:
        need(axis and all(math.isfinite(v) for v in axis)
             and all(a < b for a, b in zip(axis, axis[1:])), "Strict finite independent axes required")
        count *= len(axis)
        lines += ["AXIS " + name, " ".join(format(v, ".17g") for v in axis)]
    need(len(values) == count and all(math.isfinite(float(v)) for v in values), "Complete finite grid product required")
    return "\n".join(lines + ["DATA"] + list(values)) + "\n"

def checked_pins(pins):
    for name, digest in pins.items():
        path = Path(name)
        need(not path.is_absolute() and ".." not in path.parts, "Relative source input required")
        path = ROOT / path
        need(path.is_file() and not path.is_symlink() and sha(path) == digest, "Frozen source input changed")

def read_fixed_grid(text, expected_axes, expected_count):
    lines=text.splitlines()
    header=[]
    for name,values in expected_axes:
        header+=["AXIS "+name," ".join(format(v,".17g") for v in values)]
    need(lines[:len(header)]==header and lines[len(header)]=="DATA",
         "Exact original XYZ[T] header/axis order required; no inference or padding")
    tokens=lines[len(header)+1:]
    need(len(tokens)==expected_count and all(t and not any(c.isspace() for c in t)
         and math.isfinite(float(t)) for t in tokens),"Complete finite original tokens required")
    return tokens

def extend_cooling(tokens, original_frames):
    need(len(tokens)==original_frames*225 and original_frames in (161,81),
         "Only fixed old/born225-node histories may be extended")
    tail=tokens[-225:];addition=[]
    with localcontext() as context:
        context.prec=80
        for j in range(1,21):
            for token in tail:
                value=Decimal(300)+(Decimal(token)-Decimal(300))*Decimal(20-j)/Decimal(20)
                addition.append("300" if j==20 else format(float(value),".17g"))
    addition+=["300"]*(2*225)
    need(len(addition)==4950 and addition[-3*225:]==["300"]*(3*225),
         "Cooling reaches300 before release; both release holds remain300")
    return tokens+addition

def prepare(contract, expected):
    contract=Path(contract)
    need(contract.is_absolute() and contract.resolve()==contract and contract.is_file()
         and not contract.is_symlink() and sha(contract)==expected,"Exact external data actual required")
    c=json.loads(contract.read_text())
    need(c.get("schema")=="962-oneway-cooling-release-data-actual/v1"
         and c.get("data_preparation_authorized") is True and c.get("root_and_peer_review_complete") is True
         and all(c.get(k) is False for k in ("native_execution_authorized","head_execution_authorized",
         "engineering_accepted","physics_qualified","material_qualified","process_calibrated",
         "manufacturing_authorized","automatic_retry")),"Reviewed finite data-only authority required")
    held=json.loads((PREP/"held-preparation.json").read_text());pins=c["input_sha256"]
    need(pins.get(str((PREP/"held-preparation.json").relative_to(ROOT)))==sha(PREP/"held-preparation.json")
         and all(pins.get(k)==v for k,v in held["input_sha256"].items()),"Complete held closure required")
    checked_pins(pins)
    index=json.loads((PREP/"thermal-input-index.json").read_text())
    original=json.loads((ROOT/index["source_manifest"]["path"]).read_text())
    need(sha(ROOT/index["source_manifest"]["path"])==index["source_manifest"]["sha256"]
         and original["table_sha256"]=={n:d["sha256"] for n,d in index["table_descriptors"].items()},
         "Exact accepted original three-table manifest required")
    xs=tuple(i/8 for i in range(17));yz=tuple(i/4 for i in range(5))
    old_axes=(("X",xs[:9]),("Y",yz),("Z",yz),("T",tuple(i/400 for i in range(161))))
    born_axes=(("X",xs[8:]),("Y",yz),("Z",yz),("T",tuple(i/400 for i in range(80,161))))
    old=read_fixed_grid((SOURCE/"old-end.grid").read_text(),old_axes,36225)
    born=read_fixed_grid((SOURCE/"born-end.grid").read_text(),born_axes,18225)
    reference=(SOURCE/"born-begin80.grid").read_bytes()
    read_fixed_grid(reference.decode(),born_axes[:3],225)
    tables={
      "old-end.grid":table_text(old_axes[:3]+(("T",tuple(i/400 for i in range(183))),),extend_cooling(old,161)).encode(),
      "born-end.grid":table_text(born_axes[:3]+(("T",tuple(i/400 for i in range(80,183))),),extend_cooling(born,81)).encode(),
      "born-begin80.grid":reference}
    need(c.get("output")==str(OUTPUT) and not OUTPUT.exists() and not OUTPUT.is_symlink(),
         "One fresh fixed continuation input directory required")
    checked_pins(pins);need(sha(contract)==expected,"Actual drift")
    result={"schema":"962-oneway-cooling-release-prepared-transfer/v1",
      "source_manifest_sha256":index["source_manifest"]["sha256"],
      "original_table_sha256":original["table_sha256"],"data_actual_sha256":expected,
      "node_rows":original["node_rows"],"old_node_count":225,"born_reference_DOF_count":225,
      "shared_node_count":25,"genuinely_new_node_count":200,
      "original_tokens_preserved":54675,"new_assumed_cooling_hold_values":9900,
      "table_value_counts":{"old-end.grid":41175,"born-end.grid":23175,"born-begin80.grid":225},
      "cooling_card_sha256":sha(PREP/"card.json"),
      "birth_reference_phase":"Original exact BEGIN80 temperature on225 born DOFs incl25shared",
      "native_connectivity_or_ID_bijection_proven":False,
      "prescribed_cooling_not_heat_equation_or_process_calibration":True,
      "native_execution_authorized":False,"engineering_accepted":False,"physics_qualified":False,
      "material_qualified":False,"process_calibrated":False,"manufacturing_authorized":False}
    OUTPUT.mkdir()
    for name,body in tables.items():
        with (OUTPUT/name).open("xb") as stream:stream.write(body)
    result["table_sha256"]={name:sha(OUTPUT/name) for name in tables}
    with (OUTPUT/"transfer-manifest.json").open("x") as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write("\n")
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract",type=Path);parser.add_argument("contract_sha256")
    args=parser.parse_args();prepare(args.contract,args.contract_sha256)
