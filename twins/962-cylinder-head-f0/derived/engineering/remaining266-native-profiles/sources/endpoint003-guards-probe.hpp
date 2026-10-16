namespace SMS=CGAL::Surface_mesh_simplification;
constexpr double finest_budget_mm=0.0625;
volatile std::sig_atomic_t finest_stop_requested=0;
void finest_stop(int) { finest_stop_requested=1; }

double point_quality(const Point& a,const Point& b,const Point& c) {
  auto u=b-a,v=c-a;
  return 2*std::sqrt(3.0)*std::sqrt(CGAL::cross_product(u,v).squared_length())/
    (u.squared_length()+v.squared_length()+(v-u).squared_length());
}
struct Local_quality { std::size_t bad=0;double minimum=1; };
bool local_improves(const Local_quality& before,const Local_quality& after) {
  return after.bad<before.bad&&after.minimum>=before.minimum;
}
struct Endpoint_choice {
  Point point;std::size_t origin;Local_quality before,after;
};
using Fixed_map=Mesh::Property_map<Vertex,bool>;
struct Endpoint_placement {
  const Mesh* mesh;
  const Fixed_map* fixed;
  const std::vector<std::size_t>* origins;
  const CGAL::Polyhedral_envelope<Kernel>* envelope;
  template<class Profile> boost::optional<Endpoint_choice> choose(const Profile& profile) const {
    if(finest_stop_requested) { CGAL962_PROBE_EVENT("placement.stop");return boost::none; }
    if((*fixed)[profile.v0()]) { CGAL962_PROBE_EVENT("placement.fixed_v0");return boost::none; }
    if((*fixed)[profile.v1()]) { CGAL962_PROBE_EVENT("placement.fixed_v1");return boost::none; }
    if(!profile.left_face_exists()) { CGAL962_PROBE_EVENT("placement.no_left_face");return boost::none; }
    if(!profile.right_face_exists()) { CGAL962_PROBE_EVENT("placement.no_right_face");return boost::none; }
    const auto& fan=profile.triangles();
    if(fan.size()<=2) { CGAL962_PROBE_EVENT("placement.tiny_fan");return boost::none; }
    Local_quality before;
    for(const auto& t:fan) {
      double q=point_quality(mesh->point(t.v0),mesh->point(t.v1),mesh->point(t.v2));
      if(!std::isfinite(q)||q<=0)throw std::runtime_error("Invalid current triangle");
      before.bad+=q<2.0/29.0;before.minimum=std::min(before.minimum,q);
    }
    if(!before.bad) { CGAL962_PROBE_EVENT("placement.no_bad_before");return boost::none; }
    boost::optional<Endpoint_choice> best;
    SMS::Bounded_normal_change_filter<> normal_filter;
    for(auto endpoint:{profile.v0(),profile.v1()}) {
      probe_endpoint_origin=(*origins)[endpoint.idx()];
      CGAL962_PROBE_EVENT("placement.endpoint_begin");
      const Point p=mesh->point(endpoint);
      if(!normal_filter(profile,boost::optional<Point>(p))) { CGAL962_PROBE_EVENT("placement.normal_rejected");continue; }
      CGAL962_PROBE_EVENT("placement.normal_pass");
      if(!(*envelope)(p)) { CGAL962_PROBE_EVENT("placement.point_envelope_rejected");continue; }
      CGAL962_PROBE_EVENT("placement.point_envelope_pass");
      Local_quality after;bool admissible=true;
      // CGAL5.6 puts the two removed edge faces first. In each remaining
      // triangle, v1 is the endpoint being replaced, not a link vertex.
      for(std::size_t i=2;i<fan.size();++i) {
        const auto& t=fan[i];const auto& a=mesh->point(t.v0);const auto& c=mesh->point(t.v2);
        double q=point_quality(a,p,c);
        if(!std::isfinite(q)) { CGAL962_PROBE_EVENT("placement.triangle_nonfinite");admissible=false;break; }
        if(q<=0) { CGAL962_PROBE_EVENT("placement.triangle_nonpositive");admissible=false;break; }
        if(!(*envelope)(a,p,c)) { CGAL962_PROBE_EVENT("placement.triangle_envelope_rejected");admissible=false;break; }
        after.bad+=q<2.0/29.0;after.minimum=std::min(after.minimum,q);
      }
      if(!admissible)continue;
      probe_quality(before,after);
      if(!local_improves(before,after)) { CGAL962_PROBE_EVENT("placement.local_quality_rejected");continue; }
      CGAL962_PROBE_EVENT("placement.endpoint_admissible");
      Endpoint_choice current{p,(*origins)[endpoint.idx()],before,after};
      if(!best||current.after.bad<best->after.bad
         ||(current.after.bad==best->after.bad&&current.after.minimum>best->after.minimum)
         ||(current.after.bad==best->after.bad&&current.after.minimum==best->after.minimum
            &&current.origin<best->origin))best=current;
    }
    probe_endpoint_origin=best ? best->origin : std::numeric_limits<std::size_t>::max();
    CGAL962_PROBE_EVENT(best ? "placement.choice_present" : "placement.no_choice");
    return best;
  }
  template<class Profile> boost::optional<typename Profile::Point> operator()(const Profile& p) const {
    auto choice=choose(p);if(!choice)return boost::none;return choice->point;
  }
};
struct Quality_cost {
  const Endpoint_placement* placement;
  template<class Profile> boost::optional<typename Profile::FT> operator()(
    const Profile& profile,const boost::optional<typename Profile::Point>& point)const {
    if(!point)return boost::none;auto c=placement->choose(profile);
    if(!c)return boost::none;
    return -static_cast<double>(c->before.bad-c->after.bad);
  }
};
struct Finest_stop {
  template<class FT,class Profile> bool operator()(const FT&,const Profile&,std::size_t,std::size_t)const {
    return finest_stop_requested!=0;
  }
};
