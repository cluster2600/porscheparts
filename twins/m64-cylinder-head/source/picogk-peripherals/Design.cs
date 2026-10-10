using System.Numerics;
using PicoGKCatalog;

// All dimensions below are packaging hypotheses in the retained, uncalibrated frame.
static class Design
{
    public const float Tip=106.5f, Seat=61.1f, Retainer=101.5f, Wall=2;
    public static Vector3 Point(Vector3 o,Vector3 d,float t)=>o+d*t;
    public static float Ring(Vector3 p,Vector3 o,Vector3 d,float low,float high,float inner,float outer)=>
        MathF.Max(Es.Cyl(p,Point(o,d,low),Point(o,d,high),outer),
                 -Es.Cyl(p,Point(o,d,low-2),Point(o,d,high+2),inner));

    public static float Cover(Vector3 p,float y)
    {
        float outer=Sdf.RoundBox(p,new(0,y,107),new(45,22,21),4);
        float inner=Sdf.RoundBox(p,new(0,y,102.5f),new(42,19,22.5f),3);
        float shell=MathF.Max(outer,-inner);
        float ribs=Sdf.Capsule(p,new(-38,y,128),new(38,y,128),2);
        for(int x=-27;x<=27;x+=18)foreach(int sign in new[]{-1,1})
            ribs=Es.SMin(ribs,Sdf.Capsule(p,new(x,y,128),new(x+6,y+sign*15,127.5f),1.5f),1);
        return MathF.Min(shell,ribs);
    }

    // Cubic branching is a bio-inspired hypothesis, not an optimum for hot pulsating oil.
    public static float Radius(int leaves)=>2*MathF.Cbrt(leaves);
    static readonly List<(List<Vector3> Points,float Radius)> OuterPaths=Paths(false),InnerPaths=Paths(true);
    static List<(List<Vector3>,float)> Paths(bool extend)
    {
        var paths=new List<(List<Vector3>,float)>();
        foreach(int x in new[]{-1,1})foreach(int y in new[]{-1,1})
        {
            Vector3 fork=new(x*22.5f,-2.75f,114),end=new(x*22.5f,-2.75f+y*4,85);
            var points=Es.CubicPts(fork,fork+new Vector3(0,y*4,-6),end+new Vector3(0,0,12),end,12);
            if(extend)points.Add(end-new Vector3(0,0,6));
            paths.Add((points,Radius(1)));
        }
        return paths;
    }
    public static float OilTree(Vector3 p,float wall,bool extendPorts)
    {
        Vector3 root=new(0,-2.75f,120);
        float sdf=Es.Cyl(p,new(extendPorts?-60:-55,-2.75f,120),root,Radius(4)+wall);
        foreach(int x in new[]{-1,1})
        {
            Vector3 fork=new(x*22.5f,-2.75f,114);
            sdf=Es.SMin(sdf,Sdf.Capsule(p,root,fork,Radius(2)+wall),1);
        }
        foreach(var path in extendPorts?InnerPaths:OuterPaths)
            sdf=Es.SMin(sdf,Es.Tube(p,path.Points,path.Radius+wall),1);
        return sdf;
    }
    public static float OilOuter(Vector3 p)=>MathF.Max(OilTree(p,Wall,false),MathF.Max(-55-p.X,85-p.Z));
    public static float OilWall(Vector3 p)=>MathF.Max(OilOuter(p),-OilTree(p,0,true));
    public static float OilFluid(Vector3 p)=>MathF.Max(OilTree(p,0,true),MathF.Max(-55-p.X,85-p.Z));

    public static void Check()
    {
        void Require(bool yes){if(!yes)throw new InvalidDataException("Peripheral primitive self-check failed");}
        Require(MathF.Abs(MathF.Pow(Radius(4),3)-2*MathF.Pow(Radius(2),3))<1e-4f);
        Require(MathF.Abs(MathF.Pow(Radius(2),3)-2*MathF.Pow(Radius(1),3))<1e-4f);
        Require(MathF.Abs(Retainer-Seat-40.4f)<1e-4f);
        Require(40.4f-11.5f-22.7f>0 && 40.4f-9.6f-22.7f>0);
        Require(Cover(new(0,31,120),31)>0 && Cover(new(0,31,127),31)<0);
        Require(Cover(new(0,31,85),31)>0 && Cover(new(44,31,107),31)<0);
        Require(OilFluid(new(-54,-2.75f,120))<0 && OilWall(new(-54,-2.75f,120))>0);
        foreach(int x in new[]{-1,1})foreach(int y in new[]{-1,1})
        {
            Require(OilFluid(new(x*22.5f,-2.75f+y*4,85.5f))<0);
            Require(OilWall(new(x*22.5f,-2.75f+y*4,85.5f))>0);
        }
        Require(Ring(new(10,0,58),Vector3.Zero,Vector3.UnitZ,56.6f,59.6f,7.75f,16)<0);
        Require(Ring(new(0,0,58),Vector3.Zero,Vector3.UnitZ,56.6f,59.6f,7.75f,16)>0);
        foreach(int sign in new[]{-1,1})
        {
            Vector3 d=new(0,sign*.1391731f,.9902681f),a=81*d,b=Tip*d;
            Vector3 lo=Vector3.Min(a,b)-new Vector3(4),hi=Vector3.Max(a,b)+new Vector3(4);
            Require(a.Y-3>=lo.Y&&a.Y+3<=hi.Y&&b.Y-3>=lo.Y&&b.Y+3<=hi.Y);
        }
    }
}
