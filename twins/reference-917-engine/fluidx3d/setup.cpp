#include "setup.hpp"

#include <cstdlib>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <vector>


static uint env_uint(const char* name, const uint fallback) {
	const char* value = std::getenv(name);
	return value==nullptr ? fallback : (uint)std::strtoul(value, nullptr, 10);
}


static string env_string(const char* name, const string& fallback) {
	const char* value = std::getenv(name);
	return value==nullptr ? fallback : string(value);
}


static float env_float(const char* name, const float fallback) {
	const char* value = std::getenv(name);
	return value==nullptr ? fallback : std::strtof(value, nullptr);
}


static string json_number(const double value) {
	if(!std::isfinite(value)) return "null";
	std::ostringstream stream;
	stream << std::setprecision(10) << value;
	return stream.str();
}


struct OutletSample {
	double temperature_k = 0.0;
	double mass_flow_kg_s = 0.0;
	double heat_rejection_w = 0.0;
	double effective_h_w_m2k = 0.0;
	double density_delta_pressure_pa = 0.0;
	ulong cells = 0ull;
};


static OutletSample sample_outlet(
	LBM& lbm,
	const float si_domain_x,
	const float si_velocity,
	const float lbm_velocity,
	const float si_density,
	const float si_air_temperature,
	const float si_wall_temperature,
	const float external_area_m2
) {
	lbm.update_fields();
	lbm.u.read_from_device();
	lbm.rho.read_from_device();
	lbm.T.read_from_device();

	const uint nx=lbm.get_Nx(), ny=lbm.get_Ny(), nz=lbm.get_Nz();
	double temperature_flux = 0.0;
	double velocity_flux = 0.0;
	double inlet_density = 0.0;
	double outlet_density = 0.0;
	ulong outlet_cells = 0ull;
	for(uint z=1u; z<nz-1u; z++) {
		for(uint y=1u; y<ny-1u; y++) {
			const ulong inlet = lbm.index(1u, y, z);
			const ulong outlet = lbm.index(nx-2u, y, z);
			if((lbm.flags[outlet]&TYPE_S)==0u) {
				const double ux = fmax((double)lbm.u.x[outlet], 0.0);
				temperature_flux += ux*(double)units.si_T(lbm.T[outlet]);
				velocity_flux += ux;
				inlet_density += (double)lbm.rho[inlet];
				outlet_density += (double)lbm.rho[outlet];
				outlet_cells++;
			}
		}
	}
	OutletSample sample;
	sample.cells = outlet_cells;
	sample.temperature_k = velocity_flux>0.0
		? temperature_flux/velocity_flux : (double)si_air_temperature;
	const double cell_size_m = (double)si_domain_x/(double)nx;
	const double volume_flow_m3_s = velocity_flux*cell_size_m*cell_size_m
		*((double)si_velocity/(double)lbm_velocity);
	sample.mass_flow_kg_s = (double)si_density*volume_flow_m3_s;
	sample.heat_rejection_w = sample.mass_flow_kg_s*1007.0
		*(sample.temperature_k-(double)si_air_temperature);
	sample.effective_h_w_m2k = sample.heat_rejection_w/
		(external_area_m2*((double)si_wall_temperature-(double)si_air_temperature));
	if(outlet_cells>0ull) {
		const double mean_inlet_density = inlet_density/(double)outlet_cells;
		const double mean_outlet_density = outlet_density/(double)outlet_cells;
		sample.density_delta_pressure_pa = units.si_p(
			(float)((mean_inlet_density-mean_outlet_density)/3.0)
		);
	}
	return sample;
}


void main_setup() {
	// Le Mach LBM reste inférieur à 0,11; les grandeurs SI sont celles du point
	// burst F34. La température solide est imposée, comme dans le cas OpenFOAM.
	const uint Nx = env_uint("F34_NX", 192u);
	const uint Ny = env_uint("F34_NY", 120u);
	const uint Nz = env_uint("F34_NZ", 88u);
	const ulong steps = (ulong)env_uint("F34_STEPS", 5000u);
	const ulong chunk_steps = (ulong)env_uint("F34_CHUNK_STEPS", 250u);
	const float si_domain_x = env_float("F34_DOMAIN_X_M", 0.600f);
	const float si_head_longest_side = env_float("F34_HEAD_LONGEST_SIDE_M", 0.208364f);
	const float si_velocity = env_float("F34_VELOCITY_M_S", 77.0f);
	const float si_density = env_float("F34_DENSITY_KG_M3", 1.06f);
	const float si_nu = env_float("F34_NU_M2_S", 1.93396E-5f);
	const float si_alpha_molecular = env_float("F34_MOLECULAR_ALPHA_M2_S", 2.86E-5f);
	const float turbulence_intensity = 0.05f;
	const float mixing_length_m = 0.012f;
	const float turbulent_prandtl = 0.85f;
	const float c_mu = 0.09f;
	const float turbulent_k_m2_s2 = 1.5f*sq(si_velocity*turbulence_intensity);
	const float eddy_nu_m2_s = powf(c_mu, 0.25f)*sqrtf(turbulent_k_m2_s2)*mixing_length_m;
	const float modelled_effective_alpha = si_alpha_molecular+eddy_nu_m2_s/turbulent_prandtl;
	const float si_alpha = env_float("F34_EFFECTIVE_ALPHA_M2_S", modelled_effective_alpha);
	const float si_air_temperature = env_float("F34_AIR_TEMPERATURE_K", 308.15f);
	const float si_wall_temperature = env_float("F34_WALL_TEMPERATURE_K", 533.15f);
	const float external_area_m2 = env_float("F34_EXTERNAL_AREA_M2", 0.6703955311f);
	const float domain_cross_section_m2 = env_float("F34_DOMAIN_CROSS_SECTION_M2", 0.36f*0.26f);
	const float lbm_velocity = env_float("F34_LBM_VELOCITY", 0.060f);

	units.set_m_kg_s_K(
		(float)Nx,
		lbm_velocity,
		1.0f,
		1.0f,
		si_domain_x,
		si_velocity,
		si_density,
		si_air_temperature
	);
	const float lbm_nu = units.nu(si_nu);
	const float lbm_alpha = units.alpha(si_alpha);
	LBM lbm(Nx, Ny, Nz, lbm_nu, 0.0f, 0.0f, 0.0f, 0.0f, lbm_alpha, 0.0f);

	const string stl_path = env_string(
		"F34_STL",
		get_exe_path()+"../stl/917-head-aircooled-4v-f34-external-cooling-envelope-binary.stl"
	);
	Mesh* mesh = read_stl(
		stl_path,
		lbm.size(),
		lbm.center(),
		units.x(si_head_longest_side)
	);
	lbm.voxelize_mesh_on_device(mesh, TYPE_S);
	delete mesh;
	lbm.flags.read_from_device();

	const float lbm_air_temperature = units.T(si_air_temperature);
	const float lbm_wall_temperature = units.T(si_wall_temperature);
	const uint nx=lbm.get_Nx(), ny=lbm.get_Ny(), nz=lbm.get_Nz();
	// FluidX3D applique TYPE_T sur une cellule fluide. Une cellule TYPE_S|TYPE_T
	// reste un solide adiabatique, car le noyau fluide retourne avant la
	// collision D3Q7. On construit donc une couche fluide isotherme d'une maille
	// autour de la peau voxelisée et on conserve la peau comme paroi no-slip.
	std::vector<uchar> hot_wall(lbm.get_N(), 0u);
	parallel_for(lbm.get_N(), [&](ulong n) {
		uint x=0u, y=0u, z=0u;
		lbm.coordinates(n, x, y, z);
		if((lbm.flags[n]&TYPE_S)!=0u||x==0u||x==nx-1u||y==0u||y==ny-1u||z==0u||z==nz-1u) return;
		const bool adjacent_solid =
			(lbm.flags[lbm.index(x-1u, y, z)]&TYPE_S)!=0u||
			(lbm.flags[lbm.index(x+1u, y, z)]&TYPE_S)!=0u||
			(lbm.flags[lbm.index(x, y-1u, z)]&TYPE_S)!=0u||
			(lbm.flags[lbm.index(x, y+1u, z)]&TYPE_S)!=0u||
			(lbm.flags[lbm.index(x, y, z-1u)]&TYPE_S)!=0u||
			(lbm.flags[lbm.index(x, y, z+1u)]&TYPE_S)!=0u;
		hot_wall[n] = adjacent_solid ? 1u : 0u;
	});
	parallel_for(lbm.get_N(), [&](ulong n) {
		uint x=0u, y=0u, z=0u;
		lbm.coordinates(n, x, y, z);
		if((lbm.flags[n]&TYPE_S)!=0u) {
			lbm.flags[n] = TYPE_S|TYPE_X;
		} else {
			lbm.u.x[n] = lbm_velocity;
			lbm.u.y[n] = 0.0f;
			lbm.u.z[n] = 0.0f;
			lbm.T[n] = lbm_air_temperature;
			if(hot_wall[n]!=0u) {
				lbm.flags[n] = TYPE_T;
				lbm.T[n] = lbm_wall_temperature;
			}
		}
		if(x==0u||x==nx-1u||y==0u||y==ny-1u||z==0u||z==nz-1u) {
			lbm.flags[n] = TYPE_E|TYPE_T;
			lbm.u.x[n] = lbm_velocity;
			lbm.u.y[n] = 0.0f;
			lbm.u.z[n] = 0.0f;
			lbm.T[n] = lbm_air_temperature;
		}
	});

	const ulong minimum_steps = (ulong)ceil(1.25*(double)Nx/(double)lbm_velocity);
	OutletSample sample;
	double previous_temperature_k = -1.0;
	double convergence_delta_k = 1.0E30;
	double convergence_relative = 1.0E30;
	uint stable_checks = 0u;
	bool converged = false;
	std::vector<double> temperature_history;
	const size_t minimum_statistical_samples = (size_t)env_uint("F34_MINIMUM_STATISTICAL_SAMPLES", 40u);
	while(lbm.get_t()<steps) {
		const ulong remaining = steps-lbm.get_t();
		lbm.run(min(chunk_steps, remaining), steps);
		sample = sample_outlet(
			lbm, si_domain_x, si_velocity, lbm_velocity, si_density,
			si_air_temperature, si_wall_temperature, external_area_m2
		);
		if(lbm.get_t()>=minimum_steps && std::isfinite(sample.temperature_k)) {
			temperature_history.push_back(sample.temperature_k);
		}
		if(temperature_history.size()>=minimum_statistical_samples) {
			double previous_mean = 0.0, current_mean = 0.0;
			const size_t n = temperature_history.size();
			const size_t half = n/2u;
			for(size_t i=0u; i<half; i++) previous_mean += temperature_history[i];
			for(size_t i=half; i<2u*half; i++) current_mean += temperature_history[i];
			previous_mean /= (double)half;
			current_mean /= (double)half;
			convergence_delta_k = fabs(current_mean-previous_mean);
			convergence_relative = convergence_delta_k/fmax(fabs(current_mean), 1.0);
		} else {
			convergence_delta_k = previous_temperature_k>0.0
				? fabs(sample.temperature_k-previous_temperature_k) : 1.0E30;
			convergence_relative = 1.0E30;
		}
		const bool stable = lbm.get_t()>=minimum_steps
			&& sample.heat_rejection_w>0.0
			&& std::isfinite(sample.temperature_k)
			&& temperature_history.size()>=minimum_statistical_samples
			&& convergence_relative<0.01;
		stable_checks = stable ? stable_checks+1u : 0u;
		previous_temperature_k = sample.temperature_k;
		if(stable_checks>=3u) {
			converged = true;
			break;
		}
	}
	const ulong actual_steps = lbm.get_t();
	if(temperature_history.size()>=minimum_statistical_samples) {
		const size_t begin = temperature_history.size()/2u;
		double averaged_temperature_k = 0.0;
		for(size_t i=begin; i<temperature_history.size(); i++) averaged_temperature_k += temperature_history[i];
		sample.temperature_k = averaged_temperature_k/(double)(temperature_history.size()-begin);
		sample.heat_rejection_w = sample.mass_flow_kg_s*1007.0
			*(sample.temperature_k-(double)si_air_temperature);
		sample.effective_h_w_m2k = sample.heat_rejection_w/
			((double)external_area_m2*((double)si_wall_temperature-(double)si_air_temperature));
	}
	const double cell_size_m = (double)si_domain_x/(double)Nx;
	const bool temperature_bounded = sample.temperature_k>=(double)si_air_temperature-1.0
		&& sample.temperature_k<=(double)si_wall_temperature+1.0;
	const bool heat_direction_physical = sample.heat_rejection_w>=0.0;
	const bool numerically_stable = std::isfinite(sample.temperature_k)
		&& std::isfinite(sample.heat_rejection_w)
		&& std::isfinite(sample.density_delta_pressure_pa)
		&& temperature_bounded
		&& heat_direction_physical;
	if(!numerically_stable) converged = false;
	const float3 force_lbm = lbm.object_force(TYPE_S|TYPE_X);
	const double drag_force_n = numerically_stable ? fabs((double)units.si_F(force_lbm.x)) : NAN;
	const double pressure_drop_from_drag_pa = drag_force_n/domain_cross_section_m2;

	const string result_path = env_string("F34_RESULT", "f34-fluidx3d-result.json");
	const string phase = env_string("F34_PHASE", "F34");
	std::ofstream result(result_path);
	result << std::setprecision(10)
		<< "{\n"
		<< "  \"schema_version\": \"1.0.0\",\n"
		<< "  \"phase\": \"" << phase << "\",\n"
		<< "  \"solver\": \"FluidX3D_D3Q19_TRT_FP32_SUBGRID_TEMPERATURE\",\n"
		<< "  \"classification\": \"independent_LBM_external_cooling_fixed_wall_temperature\",\n"
		<< "  \"thermal_closure\": \"constant_effective_diffusivity_sensitivity\",\n"
		<< "  \"grid\": [" << Nx << ", " << Ny << ", " << Nz << "],\n"
		<< "  \"cell_size_mm\": " << 1000.0*cell_size_m << ",\n"
		<< "  \"requested_max_steps\": " << steps << ",\n"
		<< "  \"actual_steps\": " << actual_steps << ",\n"
		<< "  \"minimum_flow_through_steps\": " << minimum_steps << ",\n"
		<< "  \"convergence_delta_temperature_k\": " << convergence_delta_k << ",\n"
		<< "  \"convergence_relative_two_half_means\": " << convergence_relative << ",\n"
		<< "  \"convergence_samples\": " << temperature_history.size() << ",\n"
		<< "  \"minimum_statistical_samples\": " << minimum_statistical_samples << ",\n"
		<< "  \"mach_lbm\": " << units.Ma(lbm_velocity) << ",\n"
		<< "  \"velocity_m_s\": " << si_velocity << ",\n"
		<< "  \"domain_x_m\": " << si_domain_x << ",\n"
		<< "  \"domain_cross_section_m2\": " << domain_cross_section_m2 << ",\n"
		<< "  \"external_area_m2\": " << external_area_m2 << ",\n"
		<< "  \"molecular_thermal_diffusivity_m2_s\": " << si_alpha_molecular << ",\n"
		<< "  \"effective_thermal_diffusivity_m2_s\": " << si_alpha << ",\n"
		<< "  \"thermal_closure_inputs\": {\"turbulence_intensity\": " << turbulence_intensity
		<< ", \"mixing_length_m\": " << mixing_length_m
		<< ", \"c_mu\": " << c_mu
		<< ", \"turbulent_prandtl\": " << turbulent_prandtl << "},\n"
		<< "  \"wall_temperature_k\": " << si_wall_temperature << ",\n"
		<< "  \"inlet_temperature_k\": " << si_air_temperature << ",\n"
		<< "  \"outlet_temperature_k\": " << json_number(sample.temperature_k) << ",\n"
		<< "  \"mass_flow_kg_s\": " << json_number(sample.mass_flow_kg_s) << ",\n"
		<< "  \"heat_rejection_w\": " << json_number(sample.heat_rejection_w) << ",\n"
		<< "  \"effective_h_w_m2k\": " << json_number(sample.effective_h_w_m2k) << ",\n"
		<< "  \"drag_force_n\": " << json_number(drag_force_n) << ",\n"
		<< "  \"pressure_drop_from_drag_pa\": " << json_number(pressure_drop_from_drag_pa) << ",\n"
		<< "  \"density_delta_pressure_pa_diagnostic\": " << json_number(sample.density_delta_pressure_pa) << ",\n"
		<< "  \"outlet_sample_cells\": " << sample.cells << ",\n"
		<< "  \"temperature_bounded\": " << (temperature_bounded ? "true" : "false") << ",\n"
		<< "  \"heat_direction_physical\": " << (heat_direction_physical ? "true" : "false") << ",\n"
		<< "  \"numerically_stable\": " << (numerically_stable ? "true" : "false") << ",\n"
		<< "  \"converged\": " << (converged ? "true" : "false") << ",\n"
		<< "  \"release_claim\": false\n"
		<< "}\n";
	result.close();
	print_info("F34 result: "+result_path);
}
