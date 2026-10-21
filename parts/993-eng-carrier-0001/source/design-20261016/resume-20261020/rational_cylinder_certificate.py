"""Exact Bernstein bound for complete rational surfaces near a Y-axis cylinder."""
from fractions import Fraction as F
from math import comb


def centre_through_three(points):
    p,q,r=[[F(x)for x in row]for row in points]
    a,b=2*(q[0]-p[0]),2*(q[1]-p[1]);c,d=2*(r[0]-p[0]),2*(r[1]-p[1])
    e=sum(x*x for x in q)-sum(x*x for x in p);f=sum(x*x for x in r)-sum(x*x for x in p);det=a*d-b*c
    if not det:raise ValueError('Collinear reference points')
    return((e*d-b*f)/det,(a*f-e*c)/det)


def radial_bound(poles,weights,centre,radius):
    m,n=len(poles)-1,len(poles[0])-1;r=F(radius);cx,cz=map(F,centre)
    if r<=0 or len(weights)!=m+1 or any(len(row)!=n+1 for row in poles+weights):raise ValueError('Surface dimensions or radius differ')
    w=[[F(x)for x in row]for row in weights];minimum=min(x for row in w for x in row)
    if minimum<=0:raise ValueError('Strictly positive weights required')
    x=[[w[i][j]*(F(poles[i][j][0])-cx)for j in range(n+1)]for i in range(m+1)];z=[[w[i][j]*(F(poles[i][j][1])-cz)for j in range(n+1)]for i in range(m+1)]
    residual=[[F(0)for _ in range(2*n+1)]for _ in range(2*m+1)]
    for i in range(m+1):
        for j in range(n+1):
            for k in range(m+1):
                for l in range(n+1):
                    factor=F(comb(m,i)*comb(m,k),comb(2*m,i+k))*F(comb(n,j)*comb(n,l),comb(2*n,j+l))
                    residual[i+k][j+l]+=factor*(x[i][j]*x[k][l]+z[i][j]*z[k][l]-r*r*w[i][j]*w[k][l])
    numerator=max(abs(x)for row in residual for x in row);squared=numerator/(minimum*minimum)
    return dict(complete_radial_deviation_bound_mm=str(squared/r),maximum_squared_radius_residual_mm2=str(squared),minimum_weight=str(minimum),residual_Bernstein_coefficients=[[str(x)for x in row]for row in residual],degree=[m,n])
