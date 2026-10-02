import time

from logo_identity import build_reference_embeddings, load_model, save_reference_cache

WEIGHTS_PATH = "../../data/external/phishpedia/resnetv2_rgb_new.pth.tar"
TARGETLIST_PATH = "../../data/external/phishpedia/expand_targetlist"
CACHE_PATH = "../../data/external/phishpedia/logo_reference_embeddings.pkl"


def main():
    print("Loading model...")
    model = load_model(WEIGHTS_PATH)

    print("Building reference embeddings (one-time, cached afterward)...")
    t0 = time.time()
    embeddings, file_paths = build_reference_embeddings(TARGETLIST_PATH, model)
    elapsed = time.time() - t0

    save_reference_cache(CACHE_PATH, embeddings, file_paths)
    print(f"Done in {elapsed:.1f}s -- {len(file_paths)} logo images from "
          f"{len(set(p.split('/')[-2] for p in file_paths))} brand folders.")
    print(f"Saved to {CACHE_PATH}")


if __name__ == "__main__":
    main()
