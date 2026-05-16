from time import perf_counter
import language.source
import language.transpiler
import sys

if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise RuntimeError(f"Usage: lang.py <build | run> <path>")
    
    mode = sys.argv[1]
    path = sys.argv[2]

    src = language.source.Source(path)

    print("Building...")

    start = perf_counter()
    data = language.transpiler.PythonTranspiler(src).load().transpile()
    end = perf_counter()

    duration = end - start
    print(f"Build took {duration:.2f} seconds")

    if mode == "build":
        output_path = path.removesuffix("."+path.split(".")[-1]) + ".py"
        with open(output_path, "w") as f:
            f.write(data)
        
        print(f"Built -> {output_path}")

    elif mode == "run":
        print("Executing...\n")
        start = perf_counter()
        exec(data)
        end = perf_counter()

        duration = end - start
        print(f"\nExecution took {duration:.2f} seconds")

    else:
        raise RuntimeError(f"Invalid output mode. Usage: compile.py <build | run> <path>")

    print("Done!")