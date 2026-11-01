import { layer } from "./src/config";
import { createNetwork } from "./src/network";
import { createCompute } from "./src/compute";
export const deployment = layer === "network" ? createNetwork() : createCompute();
