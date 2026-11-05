// Local orthographic diagnostic. No geometry modification or anatomical labels.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

template<class T> std::vector<T> read(const std::string& path, size_t count) {
    std::ifstream in(path, std::ios::binary | std::ios::ate);
    if (!in || in.tellg() != std::streamoff(count * sizeof(T))) throw std::runtime_error("Input size mismatch");
    in.seekg(0);
    std::vector<T> result(count);
    if (!in.read(reinterpret_cast<char*>(result.data()), result.size()*sizeof(T))) throw std::runtime_error("Input read failed");
    return result;
}

int main(int argc, char** argv) {
    try {
        if (argc != 9) throw std::runtime_error("Expected: projected-vertices faces component-ranks Nv Nf selected-rank-or-minus-one output.ppm width");
        const size_t nv = std::stoull(argv[4]), nf = std::stoull(argv[5]);
        const int selection = std::stoi(argv[6]), width = std::stoi(argv[8]);
        if (width < 64 || width > 4096 || nv == 0 || nf == 0) throw std::runtime_error("Invalid dimensions");
        auto points = read<double>(argv[1], nv*3);
        auto faces = read<int64_t>(argv[2], nf*3);
        auto ranks = read<int32_t>(argv[3], nf);
        std::vector<bool> used(nv, false);
        for (size_t f=0; f<nf; ++f) {
            for (int j=0; j<3; ++j) if (faces[3*f+j]<0 || size_t(faces[3*f+j])>=nv) throw std::runtime_error("Invalid source index");
            if (selection < 0 || ranks[f] == selection)
                for (int j=0; j<3; ++j) used[faces[3*f+j]] = true;
        }
        double xmin=INFINITY,xmax=-INFINITY,ymin=INFINITY,ymax=-INFINITY;
        for (size_t i=0;i<nv;++i) if (used[i]) {
            for (int j=0;j<3;++j) if (!std::isfinite(points[3*i+j])) throw std::runtime_error("Nonfinite source coordinate");
            xmin=std::min(xmin,points[3*i]); xmax=std::max(xmax,points[3*i]);
            ymin=std::min(ymin,points[3*i+1]); ymax=std::max(ymax,points[3*i+1]);
        }
        double span=std::max(xmax-xmin,ymax-ymin);
        if (!(span>0) || !std::isfinite(span)) throw std::runtime_error("Empty or point-like selection");
        const double scale=(width-32)/span, cx=(xmin+xmax)/2,cy=(ymin+ymax)/2;
        for (size_t i=0;i<nv;++i) {
            points[3*i]=(points[3*i]-cx)*scale+width/2.0;
            points[3*i+1]=(points[3*i+1]-cy)*scale+width/2.0;
        }
        std::vector<double> depth(size_t(width)*width,-INFINITY);
        std::vector<unsigned char> image(size_t(width)*width*3,22);
        const std::array<std::array<int,3>,4> palette={{{185,198,213},{246,164,55},{100,215,155},{216,121,213}}};
        size_t selected=0,rasterized=0;
        for (size_t f=0;f<nf;++f) {
            if (selection>=0 && ranks[f]!=selection) continue;
            ++selected;
            const double *a=&points[3*faces[3*f]],*b=&points[3*faces[3*f+1]],*c=&points[3*faces[3*f+2]];
            const double area=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
            if (std::abs(area)<1e-16) continue;
            int loX=std::max(0,int(std::floor(std::min({a[0],b[0],c[0]}))));
            int hiX=std::min(width-1,int(std::ceil(std::max({a[0],b[0],c[0]}))));
            int loY=std::max(0,int(std::floor(std::min({a[1],b[1],c[1]}))));
            int hiY=std::min(width-1,int(std::ceil(std::max({a[1],b[1],c[1]}))));
            // Undo pixel scaling when deriving the view-space unit normal.
            double ux=(b[0]-a[0])/scale,uy=(b[1]-a[1])/scale,uz=b[2]-a[2];
            double vx=(c[0]-a[0])/scale,vy=(c[1]-a[1])/scale,vz=c[2]-a[2];
            double nx=uy*vz-uz*vy,ny=uz*vx-ux*vz,nz=ux*vy-uy*vx;
            double n=std::sqrt(nx*nx+ny*ny+nz*nz);
            double light=n>0 ? .3+.7*std::abs((.25*nx+.35*ny+.9027735*nz)/n) : .3;
            light=std::min(1.0,light);
            auto rgb=palette.at(std::min(3,std::max(0,ranks[f])));
            bool touched=false;
            for (int y=loY;y<=hiY;++y) for (int x=loX;x<=hiX;++x) {
                const double px=x+.5,py=y+.5;
                double wb=((px-a[0])*(c[1]-a[1])-(py-a[1])*(c[0]-a[0]))/area;
                double wc=((b[0]-a[0])*(py-a[1])-(b[1]-a[1])*(px-a[0]))/area,wa=1-wb-wc;
                if (std::min({wa,wb,wc}) < -1e-12) continue;
                size_t pixel=size_t(width-1-y)*width+x;
                double z=wa*a[2]+wb*b[2]+wc*c[2];
                if (z<=depth[pixel]) continue;
                depth[pixel]=z; touched=true;
                for (int j=0;j<3;++j) image[3*pixel+j]=static_cast<unsigned char>(rgb[j]*light);
            }
            rasterized+=touched;
        }
        std::ifstream existing(argv[7]);
        if (existing.good()) throw std::runtime_error("Existing output refused");
        std::ofstream out(argv[7],std::ios::binary);
        out<<"P6\n"<<width<<" "<<width<<"\n255\n";
        out.write(reinterpret_cast<char*>(image.data()),image.size());
        if (!out) throw std::runtime_error("Output write failed");
        std::cout<<"{\"selected_original_faces\":"<<selected<<",\"faces_winning_pixels\":"<<rasterized<<",\"visualization_only\":true}\n";
    } catch (const std::exception& e) { std::cerr<<e.what()<<"\n"; return 1; }
}
