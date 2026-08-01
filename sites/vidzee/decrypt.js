import { readFile } from "node:fs/promises";

async function f(w, g = {}) {
  const Y = {
    env: Object.setPrototypeOf({
      abort(A, B, C, I) {
        A = H(A >>> 0);
        B = H(B >>> 0);
        C = C >>> 0;
        I = I >>> 0;
        (() => {
          throw Error(`${A} in ${B}:${C}:${I}`);
        })();
      }
    }, Object.assign(Object.create(globalThis), g.env || {}))
  };
  const {
    exports: Q
  } = await WebAssembly.instantiate(w, Y);
  const E = Q.memory || g.env.memory;
  const o = Object.setPrototypeOf({
    decrypt(A, B) {
      A = n(e(Uint8Array, 6, 0, A) || K());
      B = i(B) || K();
      try {
        return F(Uint8Array, Q.decrypt(A, B) >>> 0);
      } finally {
        c(A);
      }
    }
  }, Q);
  function H(A) {
    if (!A) {
      return null;
    }
    const B = A + new Uint32Array(E.buffer)[A - 4 >>> 2] >>> 1;
    const C = new Uint16Array(E.buffer);
    let I = A >>> 1;
    let G = "";
    while (B - I > 1024) {
      G += String.fromCharCode(...C.subarray(I, I += 1024));
    }
    return G + String.fromCharCode(...C.subarray(I, B));
  }
  function i(A) {
    if (A == null) {
      return 0;
    }
    const B = A.length;
    const C = Q.__new(B << 1, 2) >>> 0;
    const I = new Uint16Array(E.buffer);
    for (let G = 0; G < B; ++G) {
      I[(C >>> 1) + G] = A.charCodeAt(G);
    }
    return C;
  }
  function F(A, B) {
    if (B) {
      return new A(E.buffer, U(B + 4), s.getUint32(B + 8, true) / A.BYTES_PER_ELEMENT).slice();
    } else {
      return null;
    }
  }
  function e(A, B, C, I) {
    if (I == null) {
      return 0;
    }
    const G = I.length;
    const y = Q.__pin(Q.__new(G << C, 1)) >>> 0;
    const D = Q.__new(12, B) >>> 0;
    L(D + 0, y);
    s.setUint32(D + 4, y, true);
    s.setUint32(D + 8, G << C, true);
    new A(E.buffer, y, G).set(I);
    Q.__unpin(y);
    return D;
  }
  const r = new Map();
  function n(A) {
    if (A) {
      const B = r.get(A);
      if (B) {
        r.set(A, B + 1);
      } else {
        r.set(Q.__pin(A), 1);
      }
    }
    return A;
  }
  function c(A) {
    if (A) {
      const B = r.get(A);
      if (B === 1) {
        Q.__unpin(A);
        r.delete(A);
      } else if (B) {
        r.set(A, B - 1);
      } else {
        throw Error(`invalid refcount '${B}' for reference '${A}'`);
      }
    }
  }
  function K() {
    throw TypeError("value must not be null");
  }
  let s = new DataView(E.buffer);
  function L(A, B) {
    try {
      s.setUint32(A, B, true);
    } catch {
      s = new DataView(E.buffer);
      s.setUint32(A, B, true);
    }
  }
  function U(A) {
    try {
      return s.getUint32(A, true);
    } catch {
      s = new DataView(E.buffer);
      return s.getUint32(A, true);
    }
  }
  return o;
}

const WASM_PATH = "./crypto.wasm"; // change to your file

async function l() {
  try {
    const wasmBytes = await readFile(WASM_PATH);
    const module = await WebAssembly.compile(wasmBytes);
    return await f(module, {
      env: {}
    });
  } catch (err) {
    console.error(err);
    return null;
  }
}
let t = null;
function M() {
  t ||= l();
  return t;
}
function V(w) {
  return new Uint8Array(Buffer.from(w, "base64"));
}
async function x(w) {
  const g = await M();
  if (!g) {
    return null;
  }
  try {
    const Y = "player.vidzee.wtf";
    const Q = g.decrypt(V(w), Y);
    if (!Q || !Q.length) {
      return null;
    }
    const E = new TextDecoder().decode(Q);
    return JSON.parse(E);
  } catch {
    return null;
  }
}
export { M as loadStreamCrypto, x as wasmDecrypt };

(async () => {
    const result = await x(process.argv[2]);
    console.log(result);
})();
