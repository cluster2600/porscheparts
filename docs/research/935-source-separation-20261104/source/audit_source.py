"""Inspect full acquired OBJ metadata and distinct indexed connectivity relations."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def sha(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def metadata(path, faces, expected_vertices):
    state = ["", "", ""]
    states, state_index, spans, comments, libraries = [], {}, [], [], []
    labels = np.empty(len(faces), dtype=np.int32)
    counts, vertex_count, face_count, buffer, start = Counter(), 0, 0, [], 0
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for raw in stream:
            digest.update(raw)
            body, marker, comment = raw.partition(b"#")
            if marker:
                comments.append(comment.rstrip().decode("utf-8", errors="backslashreplace"))
            pieces = body.strip().split(None, 1)
            if not pieces:
                continue
            tag = pieces[0].decode("ascii")
            value = pieces[1].decode("utf-8", errors="backslashreplace").strip() if len(pieces) > 1 else ""
            counts[tag] += 1
            if tag == "v":
                vertex_count += 1
            elif tag in ("o", "g", "usemtl"):
                state[("o", "g", "usemtl").index(tag)] = value
            elif tag == "mtllib":
                libraries.append(value)
            elif tag == "f":
                fields = value.split()
                if len(fields) != 3 or face_count >= len(faces):
                    raise ValueError("Original OBJ triangle count/arity mismatch")
                indices = [int(x.split("/")[0]) for x in fields]
                if 0 in indices:
                    raise ValueError("Original OBJ zero index")
                indices = [x - 1 if x > 0 else vertex_count + x for x in indices]
                buffer.append(indices)
                key = tuple(state)
                if key not in state_index:
                    state_index[key] = len(states)
                    states.append(list(key))
                label = state_index[key]
                labels[face_count] = label
                if spans and spans[-1]["state"] == label:
                    spans[-1]["faces"] += 1
                else:
                    spans.append({"first_original_face": face_count, "faces": 1, "state": label})
                face_count += 1
                if len(buffer) == 8192:
                    if not np.array_equal(np.array(buffer, dtype=np.int64), faces[start:face_count]):
                        raise ValueError("Raw OBJ face order differs from exact arrays")
                    start, buffer = face_count, []
    if buffer and not np.array_equal(np.array(buffer, dtype=np.int64), faces[start:face_count]):
        raise ValueError("Raw OBJ final face block differs")
    if vertex_count != expected_vertices or face_count != len(faces):
        raise ValueError("Original OBJ vertex/face scope mismatch")
    private = {"face_bearing_states_object_group_material": states, "face_spans": spans,
               "comments": comments, "declared_material_libraries": libraries}
    public = {"record_counts": dict(counts), "comment_records": len(comments),
              "face_bearing_metadata_states": len(states),
              "face_bearing_named_objects": len({s[0] for s in states if s[0]}),
              "face_bearing_named_groups": len({s[1] for s in states if s[1]}),
              "face_bearing_named_materials": len({s[2] for s in states if s[2]}),
              "all_original_OBJ_face_indices_compared": True}
    return digest.hexdigest(), private, public, labels


def topology(faces, vertex_count):
    if faces.ndim != 2 or faces.shape[1] != 3 or faces.min() < 0 or faces.max() >= vertex_count:
        raise ValueError("Invalid indexed triangles")
    if vertex_count * vertex_count >= 2**63:
        raise ValueError("Packed source edge key overflow")
    first = np.concatenate((faces[:, 0], faces[:, 1], faces[:, 2]))
    last = np.concatenate((faces[:, 1], faces[:, 2], faces[:, 0]))
    keys = np.minimum(first, last) * vertex_count + np.maximum(first, last)
    order = np.argsort(keys, kind="stable")
    sorted_keys = keys[order]
    starts = np.r_[0, np.flatnonzero(sorted_keys[1:] != sorted_keys[:-1]) + 1]
    uses = np.diff(np.r_[starts, len(keys)])
    if np.any(uses > 2):
        raise ValueError("Nonmanifold original source edge")
    paired = starts[uses == 2]
    left, right = order[paired] % len(faces), order[paired + 1] % len(faces)
    graph = coo_matrix((np.ones(2*len(paired), dtype=np.uint8),
                        (np.r_[left, right], np.r_[right, left])), shape=(len(faces), len(faces))).tocsr()
    edge_count, edge_labels = connected_components(graph, directed=False)
    unique_keys = sorted_keys[starts]
    a, b = unique_keys // vertex_count, unique_keys % vertex_count
    graph = coo_matrix((np.ones(2*len(a), dtype=np.uint8),
                        (np.r_[a, b], np.r_[b, a])), shape=(vertex_count, vertex_count)).tocsr()
    vertex_count_all, vertex_labels = connected_components(graph, directed=False)
    face_vertex_labels = vertex_labels[faces[:, 0]]
    report = {"unique_indexed_edges": len(starts), "boundary_edges": int(np.count_nonzero(uses == 1)),
              "face_edge_components": int(edge_count), "vertex_components_including_unused": int(vertex_count_all),
              "face_bearing_vertex_components": len(np.unique(face_vertex_labels)),
              "edge_component_face_counts_descending": sorted(np.bincount(edge_labels).tolist(), reverse=True),
              "vertex_component_face_counts_descending": sorted(np.bincount(face_vertex_labels)[np.bincount(face_vertex_labels) > 0].tolist(), reverse=True),
              "unreferenced_vertices": vertex_count - len(np.unique(faces)),
              "same_face_double_edge_incidence_pairs": int(np.count_nonzero(left == right))}
    return report, edge_labels.astype(np.int32), vertex_labels.astype(np.int32)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("obj", "arrays", "plan", "output"):
        p.add_argument("--" + key, type=Path, required=True)
    a = p.parse_args()
    plan = json.loads(a.plan.read_text())
    if sha(a.arrays) != plan["source_arrays_sha256"]:
        raise ValueError("Original arrays hash mismatch")
    with np.load(a.arrays, allow_pickle=False) as d:
        vertices, faces = d["vertices"], d["triangles"]
    if vertices.shape != (plan["vertex_count"], 3) or faces.shape != (plan["triangle_count"], 3):
        raise ValueError("Full source scope mismatch")
    obj_sha, private, meta, metadata_labels = metadata(a.obj, faces, len(vertices))
    if obj_sha != plan["original_obj_sha256"]:
        raise ValueError("Original OBJ hash mismatch")
    report, edge_labels, vertex_labels = topology(faces, len(vertices))
    a.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    faces.astype("<i8", copy=False).tofile(a.output / "original-faces.i64le")
    np.savez_compressed(a.output / "python-labels.npz", edge_face_labels=edge_labels,
                        vertex_labels=vertex_labels, metadata_face_labels=metadata_labels)
    (a.output / "private-metadata.json").write_text(json.dumps(private, indent=2) + "\n")
    result = {"plan_sha256": sha(a.plan), "source_sha256": sha(__file__), "original_obj_sha256": obj_sha,
              "arrays_sha256": sha(a.arrays), "face_binary_sha256": sha(a.output / "original-faces.i64le"),
              "metadata": meta, "topology": report, "all_original_faces_retained": True,
              "anatomical_labels_accepted": False, "complete_bare_head_selected": False,
              "physical_acceptance": False, "manufacturing_authorized": False}
    (a.output / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
