#include <petscsnes.h>
#include <string.h>

static PetscErrorCode residual(SNES snes, Vec x, Vec f, void *ctx)
{
  PetscFunctionBeginUser;
  PetscCall(VecCopy(x,f));
  PetscCall(VecScale(f,2.0));
  PetscCall(VecShift(f,-1.0));
  PetscFunctionReturn(PETSC_SUCCESS);
}

static PetscErrorCode jacobian(SNES snes, Vec x, Mat a, Mat b, void *ctx)
{
  PetscFunctionBeginUser;
  PetscCall(MatSetValue(b,0,0,2.0,INSERT_VALUES));
  PetscCall(MatAssemblyBegin(b,MAT_FINAL_ASSEMBLY));
  PetscCall(MatAssemblyEnd(b,MAT_FINAL_ASSEMBLY));
  PetscFunctionReturn(PETSC_SUCCESS);
}

int main(int argc,char **argv)
{
  SNES snes; KSP ksp; PC pc; Vec x,f; Mat a;
  PetscScalar value; PetscInt index = 0;
  PetscReal norm, error; PetscInt its; SNESConvergedReason reason;
  char mode[32]="ksponly";
  PetscCall(PetscInitialize(&argc,&argv,NULL,NULL));
  PetscCall(PetscOptionsGetString(NULL,NULL,"-case_mode",mode,sizeof(mode),NULL));
  PetscCall(VecCreateSeq(PETSC_COMM_SELF,1,&x));
  PetscCall(VecDuplicate(x,&f));
  PetscCall(VecSet(x,0));
  PetscCall(MatCreateSeqAIJ(PETSC_COMM_SELF,1,1,1,NULL,&a));
  PetscCall(SNESCreate(PETSC_COMM_SELF,&snes));
  PetscCall(SNESSetType(snes,mode));
  PetscCall(SNESSetFunction(snes,f,residual,NULL));
  PetscCall(SNESSetJacobian(snes,a,a,jacobian,NULL));
  PetscCall(SNESSetTolerances(snes,1e-10,0,0,30,1000));
  PetscCall(SNESGetKSP(snes,&ksp));
  PetscCall(KSPSetType(ksp,KSPRICHARDSON));
  PetscCall(KSPRichardsonSetScale(ksp,0.25));
  PetscCall(KSPGetPC(ksp,&pc));
  PetscCall(PCSetType(pc,PCNONE));
  PetscCall(KSPSetNormType(ksp,KSP_NORM_UNPRECONDITIONED));
  PetscCall(KSPSetConvergenceTest(ksp,KSPConvergedSkip,NULL,NULL));
  PetscCall(KSPSetTolerances(ksp,PETSC_DEFAULT,PETSC_DEFAULT,PETSC_DEFAULT,3));
  PetscCall(SNESSolve(snes,NULL,x));
  PetscCall(SNESGetConvergedReason(snes,&reason));
  PetscCall(SNESGetIterationNumber(snes,&its));
  PetscCall(residual(snes,x,f,NULL));
  PetscCall(VecNorm(f,NORM_2,&norm));
  PetscCall(VecGetValues(x,1,&index,&value));
  error = PetscAbsScalar(2.0*value-1.0);
  PetscCheck(error == norm,PETSC_COMM_SELF,PETSC_ERR_PLIB,"Residual readback disagrees");
  if (!strcmp(mode,SNESKSPONLY)) {
    PetscCheck(its == 1 && reason == SNES_CONVERGED_ITS && error == 0.125,PETSC_COMM_SELF,PETSC_ERR_PLIB,"Unexpected single-correction behavior");
  } else {
    PetscCheck(!strcmp(mode,SNESNEWTONLS) && its > 1 && reason > 0 && error <= 1e-10,PETSC_COMM_SELF,PETSC_ERR_PLIB,"Newton witness failed absolute target");
  }
  PetscCall(PetscPrintf(PETSC_COMM_SELF,"{\"mode\":\"%s\",\"reason\":%d,\"iterations\":%d,\"independent_residual\":%.17g,\"absolute_target\":1e-10}\n",mode,(int)reason,(int)its,(double)norm));
  PetscCall(SNESDestroy(&snes));
  PetscCall(MatDestroy(&a));
  PetscCall(VecDestroy(&x));
  PetscCall(VecDestroy(&f));
  PetscCall(PetscFinalize());
  return 0;
}
