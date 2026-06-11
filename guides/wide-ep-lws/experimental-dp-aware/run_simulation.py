import math
import time
import json
import os

class UnitConverter:
    """Helper class to convert between standard oilfield units and SI units."""
    
    @staticmethod
    def bar_to_pa(bar):
        return bar * 1e5
        
    @staticmethod
    def pa_to_bar(pa):
        return pa / 1e5

    @staticmethod
    def psi_to_pa(psi):
        return psi * 6894.75729
    
    @staticmethod
    def pa_to_psi(pa):
        return pa / 6894.75729
        
    @staticmethod
    def md_to_m2(md):
        return md * 9.869233e-16
        
    @staticmethod
    def m2_to_md(m2):
        return m2 / 9.869233e-16
        
    @staticmethod
    def cp_to_pas(cp):
        return cp * 1e-3
        
    @staticmethod
    def pas_to_cp(pas):
        return pas / 1e-3
        
    @staticmethod
    def bbl_day_to_m3_s(bbl_day):
        return bbl_day * 1.84013e-6

    @staticmethod
    def m3_s_to_bbl_day(m3_s):
        return m3_s / 1.84013e-6
        
    @staticmethod
    def days_to_seconds(days):
        return days * 86400.0

    @staticmethod
    def seconds_to_days(seconds):
        return seconds / 86400.0


class SparseMatrix:
    """A simple Dictionary-Of-Keys (DOK) sparse matrix implementation."""
    def __init__(self, size):
        self.size = size
        self.rows = [{} for _ in range(size)]
        
    def add(self, r, c, val):
        self.rows[r][c] = self.rows[r].get(c, 0.0) + val
        
    def set(self, r, c, val):
        self.rows[r][c] = val
        
    def get(self, r, c):
        return self.rows[r].get(c, 0.0)
        
    def dot(self, x):
        """Matrix-vector product: y = A * x"""
        y = [0.0] * self.size
        for r in range(self.size):
            row = self.rows[r]
            val = 0.0
            for c, coef in row.items():
                val += coef * x[c]
            y[r] = val
        return y


class LinearSolver:
    """Iterative solvers for AX = B."""
    
    @staticmethod
    def l2_residual_norm(A, x, b):
        Ax = A.dot(x)
        return math.sqrt(sum((bi - axi)**2 for bi, axi in zip(b, Ax)))

    @staticmethod
    def solve_cg(A, b, x0=None, max_iter=1000, tol=1e-6):
        n = len(b)
        x = [0.0] * n if x0 is None else list(x0)
        
        # Initial residual r = b - A*x
        Ax = A.dot(x)
        r = [bi - axi for bi, axi in zip(b, Ax)]
        p = list(r)
        rsold = sum(ri * ri for ri in r)
        
        if math.sqrt(rsold) < tol:
            return x, 0
            
        for i in range(max_iter):
            Ap = A.dot(p)
            pAp = sum(pi * api for pi, api in zip(p, Ap))
            if abs(pAp) < 1e-20:
                break
            alpha = rsold / pAp
            
            for j in range(n):
                x[j] += alpha * p[j]
                r[j] -= alpha * Ap[j]
                
            rsnew = sum(ri * ri for ri in r)
            if math.sqrt(rsnew) < tol:
                return x, i + 1
                
            beta = rsnew / rsold
            for j in range(n):
                p[j] = r[j] + beta * p[j]
            rsold = rsnew
            
        return x, max_iter

    @staticmethod
    def solve_jacobi(A, b, x0=None, max_iter=2000, tol=1e-6):
        n = len(b)
        x = [0.0] * n if x0 is None else list(x0)
        x_new = [0.0] * n
        
        for iteration in range(max_iter):
            for r in range(n):
                diag = A.get(r, r)
                if abs(diag) < 1e-15:
                    raise ZeroDivisionError(f"Zero diagonal element at row {r}")
                
                sum_offdiag = 0.0
                for c, val in A.rows[r].items():
                    if c != r:
                        sum_offdiag += val * x[c]
                        
                x_new[r] = (b[r] - sum_offdiag) / diag
                
            res_norm = LinearSolver.l2_residual_norm(A, x_new, b)
            if res_norm < tol:
                return x_new, iteration + 1
            x = list(x_new)
            
        return x, max_iter

    @staticmethod
    def solve_gauss_seidel(A, b, x0=None, max_iter=2000, tol=1e-6):
        n = len(b)
        x = [0.0] * n if x0 is None else list(x0)
        
        for iteration in range(max_iter):
            for r in range(n):
                diag = A.get(r, r)
                if abs(diag) < 1e-15:
                    raise ZeroDivisionError(f"Zero diagonal element at row {r}")
                
                sum_offdiag = 0.0
                for c, val in A.rows[r].items():
                    if c != r:
                        sum_offdiag += val * x[c]
                        
                x[r] = (b[r] - sum_offdiag) / diag
                
            res_norm = LinearSolver.l2_residual_norm(A, x, b)
            if res_norm < tol:
                return x, iteration + 1
                
        return x, max_iter


class Fluid:
    """Represents the fluid properties."""
    def __init__(self, viscosity, compressibility):
        self.viscosity = viscosity  # Pa.s
        self.compressibility = compressibility  # 1/Pa


class Grid:
    """Represents a 3D block-centered grid with heterogeneous properties."""
    def __init__(self, nx, ny, nz, dx, dy, dz, kx, ky, kz, porosity):
        self.nx = nx
        self.ny = ny
        self.nz = nz
        
        if isinstance(dx, (int, float)):
            self.dx = [float(dx)] * nx
        else:
            self.dx = list(dx)
        if isinstance(dy, (int, float)):
            self.dy = [float(dy)] * ny
        else:
            self.dy = list(dy)
        if isinstance(dz, (int, float)):
            self.dz = [float(dz)] * nz
        else:
            self.dz = list(dz)
            
        self.size = nx * ny * nz
        self.kx = self._to_list(kx, self.size)
        self.ky = self._to_list(ky, self.size)
        self.kz = self._to_list(kz, self.size)
        self.porosity = self._to_list(porosity, self.size)
        
        self.pore_volume = [0.0] * self.size
        self._calculate_pore_volumes()
        
    def _to_list(self, val, size):
        if isinstance(val, (int, float)):
            return [float(val)] * size
        return list(val)
        
    def get_index(self, i, j, k):
        return i + j * self.nx + k * self.nx * self.ny
        
    def get_coords(self, u):
        k = u // (self.nx * self.ny)
        j = (u % (self.nx * self.ny)) // self.nx
        i = u % self.nx
        return i, j, k
        
    def _calculate_pore_volumes(self):
        for u in range(self.size):
            i, j, k = self.get_coords(u)
            v_bulk = self.dx[i] * self.dy[j] * self.dz[k]
            self.pore_volume[u] = v_bulk * self.porosity[u]
            
    def get_transmissibility_x(self, i, j, k):
        """Transmissibility between (i, j, k) and (i+1, j, k)"""
        u1 = self.get_index(i, j, k)
        u2 = self.get_index(i + 1, j, k)
        if self.kx[u1] == 0.0 or self.kx[u2] == 0.0:
            return 0.0
        area = self.dy[j] * self.dz[k]
        dx1 = self.dx[i]
        dx2 = self.dx[i+1]
        denom = (dx1 / self.kx[u1]) + (dx2 / self.kx[u2])
        return 2.0 * area / denom

    def get_transmissibility_y(self, i, j, k):
        """Transmissibility between (i, j, k) and (i, j+1, k)"""
        u1 = self.get_index(i, j, k)
        u2 = self.get_index(i, j + 1, k)
        if self.ky[u1] == 0.0 or self.ky[u2] == 0.0:
            return 0.0
        area = self.dx[i] * self.dz[k]
        dy1 = self.dy[j]
        dy2 = self.dy[j+1]
        denom = (dy1 / self.ky[u1]) + (dy2 / self.ky[u2])
        return 2.0 * area / denom

    def get_transmissibility_z(self, i, j, k):
        """Transmissibility between (i, j, k) and (i, j, k+1)"""
        u1 = self.get_index(i, j, k)
        u2 = self.get_index(i, j, k + 1)
        if self.kz[u1] == 0.0 or self.kz[u2] == 0.0:
            return 0.0
        area = self.dx[i] * self.dy[j]
        dz1 = self.dz[k]
        dz2 = self.dz[k+1]
        denom = (dz1 / self.kz[u1]) + (dz2 / self.kz[u2])
        return 2.0 * area / denom


class Well:
    """Represents a producer or injector well with custom control (BHP or Rate)."""
    def __init__(self, name, i, j, k, control_type, target_value, skin=0.0, r_w=0.1):
        self.name = name
        self.i = i
        self.j = j
        self.k = k
        self.control_type = control_type.lower()  # "rate" or "bhp"
        self.target_value = target_value  # target rate in m3/s or BHP in Pa
        self.skin = skin
        self.r_w = r_w
        self.well_index = None
        
    def calculate_well_index(self, grid, viscosity):
        u = grid.get_index(self.i, self.j, self.k)
        kx = grid.kx[u]
        ky = grid.ky[u]
        dx = grid.dx[self.i]
        dy = grid.dy[self.j]
        dz = grid.dz[self.k]
        
        if kx == 0.0 or ky == 0.0:
            self.well_index = 0.0
            return
            
        # Peaceman equivalent radius for anisotropic reservoir
        ratio_yx = math.sqrt(ky / kx)
        ratio_xy = math.sqrt(kx / ky)
        numerator = math.sqrt(ratio_yx * (dx ** 2) + ratio_xy * (dy ** 2))
        denominator = (ky / kx) ** 0.25 + (kx / ky) ** 0.25
        r_o = 0.28 * numerator / denominator
        
        kh = math.sqrt(kx * ky)
        self.well_index = (2.0 * math.pi * kh * dz) / (viscosity * (math.log(r_o / self.r_w) + self.skin))


class SimulationState:
    """Container for the transient state of the simulation."""
    def __init__(self, size, initial_pressure):
        self.pressure = [initial_pressure] * size
        self.time = 0.0
        self.time_step = 0
        self.well_rates = {}
        self.well_bhps = {}
        self.pressures_history = []
        self.times = []


class Simulator:
    """Orchestrates the simulation execution and linear system assembly."""
    def __init__(self, grid, fluid, wells, initial_pressure, solver_type="cg", tol=1e-6, max_iter=1000):
        self.grid = grid
        self.fluid = fluid
        self.wells = wells
        self.solver_type = solver_type
        self.tol = tol
        self.max_iter = max_iter
        
        # Precompute well indices
        for well in self.wells:
            well.calculate_well_index(self.grid, self.fluid.viscosity)
            
        # Initialize state
        self.state = SimulationState(self.grid.size, initial_pressure)
        for well in self.wells:
            self.state.well_rates[well.name] = []
            self.state.well_bhps[well.name] = []
            
    def run(self, time_steps):
        print(f"Starting simulation. Grid size: {self.grid.nx}x{self.grid.ny}x{self.grid.nz} ({self.grid.size} cells)")
        print(f"Solver selected: {self.solver_type.upper()}")
        print("-" * 50)
        
        start_time = time.time()
        
        # Save initial state
        self.state.pressures_history.append(list(self.state.pressure))
        self.state.times.append(0.0)
        
        current_time = 0.0
        for step_idx, dt in enumerate(time_steps):
            current_time += dt
            self.state.time_step += 1
            
            # Assemble A and b
            A, b = self._assemble_system(dt)
            
            # Solve A * p_new = b
            p_new = self._solve(A, b, self.state.pressure)
            
            # Update state
            self.state.pressure = p_new
            self.state.time = current_time
            self.state.times.append(current_time)
            self.state.pressures_history.append(list(p_new))
            
            # Record well metrics
            self._record_well_metrics(p_new)
            
            # Log progress
            days = UnitConverter.seconds_to_days(current_time)
            print(f"Step {self.state.time_step:03d} | Time: {days:.2f} days | Avg Pressure: {self.average_pressure() / 1e5:.2f} bar")
            
        end_time = time.time()
        print("-" * 50)
        print(f"Simulation completed successfully in {end_time - start_time:.4f} seconds.")
        
    def _assemble_system(self, dt):
        n = self.grid.size
        A = SparseMatrix(n)
        b = [0.0] * n
        
        c_t = self.fluid.compressibility
        mu = self.fluid.viscosity
        
        for u in range(n):
            i, j, k = self.grid.get_coords(u)
            pv = self.grid.pore_volume[u]
            accum_term = pv * c_t / dt
            
            a_P = accum_term
            b[u] = accum_term * self.state.pressure[u]
            
            # West (i-1)
            if i > 0:
                u_w = self.grid.get_index(i - 1, j, k)
                t_w = self.grid.get_transmissibility_x(i - 1, j, k) / mu
                A.add(u, u_w, -t_w)
                a_P += t_w
            # East (i+1)
            if i < self.grid.nx - 1:
                u_e = self.grid.get_index(i + 1, j, k)
                t_e = self.grid.get_transmissibility_x(i, j, k) / mu
                A.add(u, u_e, -t_e)
                a_P += t_e
            # South (j-1)
            if j > 0:
                u_s = self.grid.get_index(i, j - 1, k)
                t_s = self.grid.get_transmissibility_y(i, j - 1, k) / mu
                A.add(u, u_s, -t_s)
                a_P += t_s
            # North (j+1)
            if j < self.grid.ny - 1:
                u_n = self.grid.get_index(i, j + 1, k)
                t_n = self.grid.get_transmissibility_y(i, j, k) / mu
                A.add(u, u_n, -t_n)
                a_P += t_n
            # Bottom (k-1)
            if k > 0:
                u_b = self.grid.get_index(i, j, k - 1)
                t_b = self.grid.get_transmissibility_z(i, j, k - 1) / mu
                A.add(u, u_b, -t_b)
                a_P += t_b
            # Top (k+1)
            if k < self.grid.nz - 1:
                u_t = self.grid.get_index(i, j, k + 1)
                t_t = self.grid.get_transmissibility_z(i, j, k) / mu
                A.add(u, u_t, -t_t)
                a_P += t_t
                
            A.add(u, u, a_P)
            
        # Add well terms
        for well in self.wells:
            u = self.grid.get_index(well.i, well.j, well.k)
            if well.control_type == "bhp":
                A.add(u, u, well.well_index)
                b[u] += well.well_index * well.target_value
            elif well.control_type == "rate":
                b[u] += well.target_value
                
        return A, b
        
    def _solve(self, A, b, x0):
        if self.solver_type == "cg":
            sol, _ = LinearSolver.solve_cg(A, b, x0, max_iter=self.max_iter, tol=self.tol)
        elif self.solver_type == "gs":
            sol, _ = LinearSolver.solve_gauss_seidel(A, b, x0, max_iter=self.max_iter, tol=self.tol)
        elif self.solver_type == "jacobi":
            sol, _ = LinearSolver.solve_jacobi(A, b, x0, max_iter=self.max_iter, tol=self.tol)
        else:
            raise ValueError(f"Unknown solver type: {self.solver_type}")
        return sol
        
    def _record_well_metrics(self, pressure):
        for well in self.wells:
            u = self.grid.get_index(well.i, well.j, well.k)
            p_cell = pressure[u]
            if well.control_type == "bhp":
                rate = well.well_index * (well.target_value - p_cell)
                bhp = well.target_value
            elif well.control_type == "rate":
                rate = well.target_value
                if well.well_index > 0:
                    bhp = p_cell + (well.target_value / well.well_index)
                else:
                    bhp = p_cell
            
            self.state.well_rates[well.name].append(rate)
            self.state.well_bhps[well.name].append(bhp)
            
    def average_pressure(self):
        total_pore_volume = sum(self.grid.pore_volume)
        weighted_sum = sum(pv * p for pv, p in zip(self.grid.pore_volume, self.state.pressure))
        return weighted_sum / total_pore_volume

    def export_results(self, filename="simulation_results.json"):
        data = {
            "nx": self.grid.nx,
            "ny": self.grid.ny,
            "nz": self.grid.nz,
            "times": [UnitConverter.seconds_to_days(t) for t in self.state.times],
            "average_pressures_bar": [UnitConverter.pa_to_bar(sum(pv * p for pv, p in zip(self.grid.pore_volume, press)) / sum(self.grid.pore_volume)) for press in self.state.pressures_history],
            "wells": {}
        }
        
        for well in self.wells:
            data["wells"][well.name] = {
                "type": well.control_type,
                "rates_bbl_day": [UnitConverter.m3_s_to_bbl_day(r) for r in self.state.well_rates[well.name]],
                "bhps_bar": [UnitConverter.pa_to_bar(p) for p in self.state.well_bhps[well.name]]
            }
            
        data["final_pressure_bar"] = [UnitConverter.pa_to_bar(p) for p in self.state.pressure]
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Results exported successfully to {filename}")


# --- Execution and Comparison Script ---

if __name__ == "__main__":
    # Define grid size
    nx, ny, nz = 10, 10, 3
    
    # Grid blocks: 20m x 20m x 10m
    dx, dy, dz = 20.0, 20.0, 10.0
    
    # Establish heterogeneous permeability (100 mD background, 10 mD in z)
    kx = [UnitConverter.md_to_m2(100.0)] * (nx * ny * nz)
    ky = [UnitConverter.md_to_m2(100.0)] * (nx * ny * nz)
    kz = [UnitConverter.md_to_m2(10.0)] * (nx * ny * nz)
    porosity = [0.2] * (nx * ny * nz)
    
    # Let's create a high permeability channel from (0,0,0) to (9,9,2)
    # to demonstrate heterogeneity.
    grid_helper = Grid(nx, ny, nz, dx, dy, dz, kx, ky, kz, porosity)
    
    # Channel path: (0,0,0) -> (3,3,0) -> (6,6,1) -> (9,9,2)
    # We will increase permeability in these blocks to 1500 mD
    channel_coords = [
        (0,0,0), (1,1,0), (2,2,0), (3,3,0),
        (4,4,1), (5,5,1), (6,6,1),
        (7,7,2), (8,8,2), (9,9,2)
    ]
    for c in channel_coords:
        u = grid_helper.get_index(*c)
        grid_helper.kx[u] = UnitConverter.md_to_m2(1500.0)
        grid_helper.ky[u] = UnitConverter.md_to_m2(1500.0)
        grid_helper.kz[u] = UnitConverter.md_to_m2(150.0)
        grid_helper.porosity[u] = 0.28
        
    # Define fluid properties (viscosity: 1.2 cP, compressibility: 1e-9 1/Pa)
    viscosity = UnitConverter.cp_to_pas(1.2)
    compressibility = 1e-9 # 1/Pa
    fluid = Fluid(viscosity, compressibility)
    
    # Define wells:
    # 1. Injector at (0, 0, 0), BHP controlled at 320 bar
    inj_bhp = UnitConverter.bar_to_pa(320.0)
    injector = Well(name="Injector", i=0, j=0, k=0, control_type="BHP", target_value=inj_bhp, skin=0.0, r_w=0.1)
    
    # 2. Producer at (9, 9, 2), Rate controlled at -200 bbl/day (production)
    prod_rate = -UnitConverter.bbl_day_to_m3_s(200.0)
    producer = Well(name="Producer", i=9, j=9, k=2, control_type="Rate", target_value=prod_rate, skin=0.0, r_w=0.1)
    
    wells = [injector, producer]
    initial_pressure = UnitConverter.bar_to_pa(200.0) # Initial reservoir pressure: 200 bar
    
    # ----------------------------------------------------
    # Part 1: Solver Comparison on the First Time-Step
    # ----------------------------------------------------
    print("=== SOLVER PERFORMANCE COMPARISON (First Time-Step, dt = 10 Days) ===")
    dt = UnitConverter.days_to_seconds(10.0)
    
    # Temporary simulator to set up A and b
    sim_comp = Simulator(grid_helper, fluid, wells, initial_pressure)
    A, b = sim_comp._assemble_system(dt)
    x0 = [initial_pressure] * grid_helper.size
    
    # 1. Conjugate Gradient
    t_start = time.time()
    x_cg, iter_cg = LinearSolver.solve_cg(A, b, x0, max_iter=2000, tol=1e-6)
    t_cg = time.time() - t_start
    res_cg = LinearSolver.l2_residual_norm(A, x_cg, b)
    print(f"CG:     {iter_cg:3d} iterations | Time: {t_cg:.5f}s | Residual L2 Norm: {res_cg:.2e}")
    
    # 2. Gauss-Seidel
    t_start = time.time()
    x_gs, iter_gs = LinearSolver.solve_gauss_seidel(A, b, x0, max_iter=2000, tol=1e-6)
    t_gs = time.time() - t_start
    res_gs = LinearSolver.l2_residual_norm(A, x_gs, b)
    print(f"GS:     {iter_gs:3d} iterations | Time: {t_gs:.5f}s | Residual L2 Norm: {res_gs:.2e}")
    
    # 3. Jacobi
    t_start = time.time()
    x_jac, iter_jac = LinearSolver.solve_jacobi(A, b, x0, max_iter=2000, tol=1e-6)
    t_jac = time.time() - t_start
    res_jac = LinearSolver.l2_residual_norm(A, x_jac, b)
    print(f"Jacobi: {iter_jac:3d} iterations | Time: {t_jac:.5f}s | Residual L2 Norm: {res_jac:.2e}")
    print("=====================================================================\n")
    
    # ----------------------------------------------------
    # Part 2: Running the Full Simulation (100 days)
    # ----------------------------------------------------
    time_steps = [UnitConverter.days_to_seconds(10.0)] * 10
    sim = Simulator(grid_helper, fluid, wells, initial_pressure, solver_type="cg")
    sim.run(time_steps)
    
    # Export results
    sim.export_results("simulation_results.json")
    
    # Print 2D Slices for Visual Inspection
    print("\n=== FINAL RESERVOIR PRESSURE SLICES ===")
    min_p = min(sim.state.pressure)
    max_p = max(sim.state.pressure)
    
    for k in range(nz):
        print(f"\n--- Layer {k+1} ---")
        for j in range(ny):
            row = []
            for i in range(nx):
                u = grid_helper.get_index(i, j, k)
                p_bar = UnitConverter.pa_to_bar(sim.state.pressure[u])
                row.append(f"{p_bar:6.1f}")
            print(" ".join(row))
    print("=======================================")
