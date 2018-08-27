module E :
  sig
    val logChannel : out_channel ref
    val debugFlag : bool ref
    val verboseFlag : bool ref
    val colorFlag : bool ref
    val redEscStr : string
    val greenEscStr : string
    val yellowEscStr : string
    val blueEscStr : string
    val purpleEscStr : string
    val cyanEscStr : string
    val whiteEscStr : string
    val resetEscStr : string
    val warnFlag : bool ref
    exception Error
    val error : ('a, unit, Pretty.doc, unit) format4 -> 'a
    val bug : ('a, unit, Pretty.doc, unit) format4 -> 'a
    val unimp : ('a, unit, Pretty.doc, unit) format4 -> 'a
    val s : 'a -> 'b
    val hadErrors : bool ref
    val warn : ('a, unit, Pretty.doc, unit) format4 -> 'a
    val warnOpt : ('a, unit, Pretty.doc, unit) format4 -> 'a
    val log : ('a, unit, Pretty.doc, unit) format4 -> 'a
    val logg : ('a, unit, Pretty.doc, unit) format4 -> 'a
    val null : ('a, unit, Pretty.doc, unit) format4 -> 'a
    val pushContext : (unit -> Pretty.doc) -> unit
    val popContext : unit -> unit
    val showContext : unit -> unit
    val withContext : (unit -> Pretty.doc) -> ('a -> 'b) -> 'a -> 'b
    val newline : unit -> unit
    val newHline : unit -> unit
    val getPosition : unit -> int * string * int
    val getHPosition : unit -> int * string
    val setHLine : int -> unit
    val setHFile : string -> unit
    val setCurrentLine : int -> unit
    val setCurrentFile : string -> unit
    type location =
      Errormsg.location = {
      file : string;
      line : int;
      hfile : string;
      hline : int;
    }
    val d_loc : unit -> location -> Pretty.doc
    val d_hloc : unit -> location -> Pretty.doc
    val getLocation : unit -> location
    val parse_error : string -> 'a
    val locUnknown : location
    val readingFromStdin : bool ref
    val startParsing : ?useBasename:bool -> string -> Lexing.lexbuf
    val startParsingFromString :
      ?file:string -> ?line:int -> string -> Lexing.lexbuf
    val finishParsing : unit -> unit
  end
module P :
  sig
    val debug : bool ref
    val debug_constraints : bool ref
    val debug_aliases : bool ref
    val debug_may_aliases : bool ref
    val smart_aliases : bool ref
    val print_constraints : bool ref
    val analyze_mono : bool ref
    val no_sub : bool ref
    val no_flow : bool ref
    val show_progress : bool ref
    val conservative_undefineds : bool ref
    val callHasNoSideEffects : (Cil.exp -> bool) ref
    val analyze_file : Cil.file -> unit
    val print_types : unit -> unit
    exception UnknownLocation
    val may_alias : Cil.exp -> Cil.exp -> bool
    val resolve_lval : Cil.lval -> Cil.varinfo list
    val resolve_exp : Cil.exp -> Cil.varinfo list
    val resolve_funptr : Cil.exp -> Cil.fundec list
    type absloc = Ptranal.absloc
    val absloc_of_varinfo : Cil.varinfo -> absloc
    val absloc_of_lval : Cil.lval -> absloc
    val absloc_eq : absloc -> absloc -> bool
    val absloc_e_points_to : Cil.exp -> absloc list
    val absloc_e_transitive_points_to : Cil.exp -> absloc list
    val absloc_lval_aliases : Cil.lval -> absloc list
    val d_absloc : unit -> absloc -> Pretty.doc
    val compute_results : bool -> unit
    val compute_aliases : bool -> unit
    val feature : Cil.featureDescr
  end
module DF :
  sig
    type 'a action =
      'a Dataflow.action =
        Default
      | Done of 'a
      | Post of ('a -> 'a)
    type 'a stmtaction =
      'a Dataflow.stmtaction =
        SDefault
      | SDone
      | SUse of 'a
    type 'a guardaction =
      'a Dataflow.guardaction =
        GDefault
      | GUse of 'a
      | GUnreachable
    module type ForwardsTransfer =
      sig
        val name : string
        val debug : bool ref
        type t
        val copy : t -> t
        val stmtStartData : t Inthash.t
        val pretty : unit -> t -> Pretty.doc
        val computeFirstPredecessor : Cil.stmt -> t -> t
        val combinePredecessors : Cil.stmt -> old:t -> t -> t option
        val doInstr : Cil.instr -> t -> t action
        val doStmt : Cil.stmt -> t -> t stmtaction
        val doGuard : Cil.exp -> t -> t guardaction
        val filterStmt : Cil.stmt -> bool
      end
    module ForwardsDataFlow :
      functor (T : ForwardsTransfer) ->
        sig val compute : Cil.stmt list -> unit end
    module type BackwardsTransfer =
      sig
        val name : string
        val debug : bool ref
        type t
        val pretty : unit -> t -> Pretty.doc
        val stmtStartData : t Inthash.t
        val funcExitData : t
        val combineStmtStartData : Cil.stmt -> old:t -> t -> t option
        val combineSuccessors : t -> t -> t
        val doStmt : Cil.stmt -> t action
        val doInstr : Cil.instr -> t -> t action
        val filterStmt : Cil.stmt -> Cil.stmt -> bool
      end
    module BackwardsDataFlow :
      functor (T : BackwardsTransfer) ->
        sig val compute : Cil.stmt list -> unit end
    val find_stmts : Cil.fundec -> Cil.stmt list * Cil.stmt list
  end
module IH :
  sig
    type 'a t = 'a Inthash.t
    val create : int -> 'a t
    val clear : 'a t -> unit
    val length : 'a t -> int
    val copy : 'a t -> 'a t
    val copy_into : 'a t -> 'a t -> unit
    val add : 'a t -> int -> 'a -> unit
    val replace : 'a t -> int -> 'a -> unit
    val remove : 'a t -> int -> unit
    val remove_all : 'a t -> int -> unit
    val mem : 'a t -> int -> bool
    val find : 'a t -> int -> 'a
    val find_all : 'a t -> int -> 'a list
    val tryfind : 'a t -> int -> 'a option
    val iter : (int -> 'a -> unit) -> 'a t -> unit
    val fold : (int -> 'a -> 'b -> 'b) -> 'a t -> 'b -> 'b
    val memoize : 'a t -> int -> (int -> 'a) -> 'a
    val tolist : 'a t -> (int * 'a) list
  end
module H :
  sig
    type ('a, 'b) t = ('a, 'b) Hashtbl.t
    val create : int -> ('a, 'b) t
    val clear : ('a, 'b) t -> unit
    val add : ('a, 'b) t -> 'a -> 'b -> unit
    val copy : ('a, 'b) t -> ('a, 'b) t
    val find : ('a, 'b) t -> 'a -> 'b
    val find_all : ('a, 'b) t -> 'a -> 'b list
    val mem : ('a, 'b) t -> 'a -> bool
    val remove : ('a, 'b) t -> 'a -> unit
    val replace : ('a, 'b) t -> 'a -> 'b -> unit
    val iter : ('a -> 'b -> unit) -> ('a, 'b) t -> unit
    val fold : ('a -> 'b -> 'c -> 'c) -> ('a, 'b) t -> 'c -> 'c
    val length : ('a, 'b) t -> int
    module type HashedType =
      sig type t val equal : t -> t -> bool val hash : t -> int end
    module type S =
      sig
        type key
        type 'a t
        val create : int -> 'a t
        val clear : 'a t -> unit
        val copy : 'a t -> 'a t
        val add : 'a t -> key -> 'a -> unit
        val remove : 'a t -> key -> unit
        val find : 'a t -> key -> 'a
        val find_all : 'a t -> key -> 'a list
        val replace : 'a t -> key -> 'a -> unit
        val mem : 'a t -> key -> bool
        val iter : (key -> 'a -> unit) -> 'a t -> unit
        val fold : (key -> 'a -> 'b -> 'b) -> 'a t -> 'b -> 'b
        val length : 'a t -> int
      end
    module Make :
      functor (H : HashedType) ->
        sig
          type key = H.t
          type 'a t = 'a Hashtbl.Make(H).t
          val create : int -> 'a t
          val clear : 'a t -> unit
          val copy : 'a t -> 'a t
          val add : 'a t -> key -> 'a -> unit
          val remove : 'a t -> key -> unit
          val find : 'a t -> key -> 'a
          val find_all : 'a t -> key -> 'a list
          val replace : 'a t -> key -> 'a -> unit
          val mem : 'a t -> key -> bool
          val iter : (key -> 'a -> unit) -> 'a t -> unit
          val fold : (key -> 'a -> 'b -> 'b) -> 'a t -> 'b -> 'b
          val length : 'a t -> int
        end
    val hash : 'a -> int
    external hash_param : int -> int -> 'a -> int = "caml_hash_univ_param"
      "noalloc"
  end
module U :
  sig
    val list_map : ('a -> 'b) -> 'a list -> 'b list
    val equals : 'a -> 'a -> bool
  end
module S :
  sig
    type timerModeEnum = Stats.timerModeEnum = Disabled | SoftwareTimer
    val reset : timerModeEnum -> unit
    val countCalls : bool ref
    val time : string -> ('a -> 'b) -> 'a -> 'b
    val repeattime : float -> string -> ('a -> 'b) -> 'a -> 'b
    val print : out_channel -> string -> unit
    val lookupTime : string -> float
    val timethis : ('a -> 'b) -> 'a -> 'b
    val lastTime : float ref
  end
val debug : bool ref
val collectPredicates : (Cil.fundec -> Cil.exp list) ref
val ignoreInstruction : (Cil.instr -> bool) ref
val instrHasNoSideEffects : (Cil.instr -> bool) ref
val getPredsFromInstr : (Cil.instr -> Cil.exp list) ref
module ExpIntHash :
  sig
    type key = Cil.exp
    type 'a t
    val create : int -> 'a t
    val clear : 'a t -> unit
    val copy : 'a t -> 'a t
    val add : 'a t -> key -> 'a -> unit
    val remove : 'a t -> key -> unit
    val find : 'a t -> key -> 'a
    val find_all : 'a t -> key -> 'a list
    val replace : 'a t -> key -> 'a -> unit
    val mem : 'a t -> key -> bool
    val iter : (key -> 'a -> unit) -> 'a t -> unit
    val fold : (key -> 'a -> 'b -> 'b) -> 'a t -> 'b -> 'b
    val length : 'a t -> int
  end
module type TRANSLATOR =
  sig
    type exp
    type unop = exp -> exp
    type binop = exp -> exp -> exp
    val mkTrue : unit -> exp
    val mkFalse : unit -> exp
    val mkAnd : binop
    val mkOr : binop
    val mkNot : unop
    val mkIte : exp -> exp -> exp -> exp
    val mkImp : binop
    val mkEq : binop
    val mkNe : binop
    val mkLt : binop
    val mkLe : binop
    val mkGt : binop
    val mkGe : binop
    val mkPlus : binop
    val mkTimes : binop
    val mkMinus : binop
    val mkDiv : binop
    val mkMod : binop
    val mkLShift : binop
    val mkRShift : binop
    val mkBAnd : binop
    val mkBXor : binop
    val mkBOr : binop
    val mkNeg : unop
    val mkCompl : unop
    val mkVar : string -> exp
    val mkConst : int -> exp
    val isValid : exp -> bool
  end
module NullTranslator : TRANSLATOR
module type SOLVER =
  sig
    type exp
    val transExp : Cil.exp -> exp
    val isValid : exp -> exp -> bool
  end
module Solver :
  functor (T : TRANSLATOR) ->
    sig
      type exp = T.exp
      exception NYI
      val transUnOp : Cil.unop -> T.exp -> T.exp
      val transBinOp : Cil.binop -> T.exp -> T.exp -> T.exp
      val transExp : Cil.exp -> T.exp
      val isValid : T.exp -> T.exp -> bool
    end
module NullSolver :
  sig
    type exp = NullTranslator.exp
    exception NYI
    val transUnOp : Cil.unop -> NullTranslator.exp -> NullTranslator.exp
    val transBinOp :
      Cil.binop ->
      NullTranslator.exp -> NullTranslator.exp -> NullTranslator.exp
    val transExp : Cil.exp -> NullTranslator.exp
    val isValid : NullTranslator.exp -> NullTranslator.exp -> bool
  end
module PredAbst :
  functor (S : SOLVER) ->
    sig
      type boolLat = True | False | Top | Bottom
      val combineBoolLat : boolLat -> boolLat -> boolLat
      val d_bl : unit -> boolLat -> Pretty.doc
      type funcSig = {
        mutable fsFormals : Cil.varinfo list;
        mutable fsReturn : Cil.varinfo option;
        mutable fsAllPreds : Cil.exp list;
        mutable fsFPPreds : Cil.exp list;
        mutable fsRetPreds : Cil.exp list;
      }
      type stmtState =
          ILState of boolLat IH.t list
        | StmState of boolLat IH.t
      type absState = stmtState IH.t
      type context = {
        mutable cFuncSigs : funcSig IH.t;
        mutable cPredicates : Cil.exp IH.t;
        mutable cRPredMap : int ExpIntHash.t;
        mutable cNextPred : int;
      }
      val emptyContext : unit -> context
      class returnFinderClass :
        Cil.varinfo option ref ->
        object
          method queueInstr : Cil.instr list -> unit
          method unqueueInstr : unit -> Cil.instr list
          method vattr : Cil.attribute -> Cil.attribute list Cil.visitAction
          method vattrparam : Cil.attrparam -> Cil.attrparam Cil.visitAction
          method vblock : Cil.block -> Cil.block Cil.visitAction
          method vexpr : Cil.exp -> Cil.exp Cil.visitAction
          method vfunc : Cil.fundec -> Cil.fundec Cil.visitAction
          method vglob : Cil.global -> Cil.global list Cil.visitAction
          method vinit :
            Cil.varinfo -> Cil.offset -> Cil.init -> Cil.init Cil.visitAction
          method vinitoffs : Cil.offset -> Cil.offset Cil.visitAction
          method vinst : Cil.instr -> Cil.instr list Cil.visitAction
          method vlval : Cil.lval -> Cil.lval Cil.visitAction
          method voffs : Cil.offset -> Cil.offset Cil.visitAction
          method vstmt : Cil.stmt -> Cil.stmt Cil.visitAction
          method vtype : Cil.typ -> Cil.typ Cil.visitAction
          method vvdec : Cil.varinfo -> Cil.varinfo Cil.visitAction
          method vvrbl : Cil.varinfo -> Cil.varinfo Cil.visitAction
        end
      val findReturn : Cil.fundec -> Cil.varinfo option
      class viFinderClass :
        Cil.varinfo ->
        bool ref ->
        object
          method queueInstr : Cil.instr list -> unit
          method unqueueInstr : unit -> Cil.instr list
          method vattr : Cil.attribute -> Cil.attribute list Cil.visitAction
          method vattrparam : Cil.attrparam -> Cil.attrparam Cil.visitAction
          method vblock : Cil.block -> Cil.block Cil.visitAction
          method vexpr : Cil.exp -> Cil.exp Cil.visitAction
          method vfunc : Cil.fundec -> Cil.fundec Cil.visitAction
          method vglob : Cil.global -> Cil.global list Cil.visitAction
          method vinit :
            Cil.varinfo -> Cil.offset -> Cil.init -> Cil.init Cil.visitAction
          method vinitoffs : Cil.offset -> Cil.offset Cil.visitAction
          method vinst : Cil.instr -> Cil.instr list Cil.visitAction
          method vlval : Cil.lval -> Cil.lval Cil.visitAction
          method voffs : Cil.offset -> Cil.offset Cil.visitAction
          method vstmt : Cil.stmt -> Cil.stmt Cil.visitAction
          method vtype : Cil.typ -> Cil.typ Cil.visitAction
          method vvdec : Cil.varinfo -> Cil.varinfo Cil.visitAction
          method vvrbl : Cil.varinfo -> Cil.varinfo Cil.visitAction
        end
      val expContainsVi : Cil.exp -> Cil.varinfo -> bool
      class derefFinderClass :
        'a ->
        bool ref ->
        object
          method queueInstr : Cil.instr list -> unit
          method unqueueInstr : unit -> Cil.instr list
          method vattr : Cil.attribute -> Cil.attribute list Cil.visitAction
          method vattrparam : Cil.attrparam -> Cil.attrparam Cil.visitAction
          method vblock : Cil.block -> Cil.block Cil.visitAction
          method vexpr : Cil.exp -> Cil.exp Cil.visitAction
          method vfunc : Cil.fundec -> Cil.fundec Cil.visitAction
          method vglob : Cil.global -> Cil.global list Cil.visitAction
          method vinit :
            Cil.varinfo -> Cil.offset -> Cil.init -> Cil.init Cil.visitAction
          method vinitoffs : Cil.offset -> Cil.offset Cil.visitAction
          method vinst : Cil.instr -> Cil.instr list Cil.visitAction
          method vlval : Cil.lval -> Cil.lval Cil.visitAction
          method voffs : Cil.offset -> Cil.offset Cil.visitAction
          method vstmt : Cil.stmt -> Cil.stmt Cil.visitAction
          method vtype : Cil.typ -> Cil.typ Cil.visitAction
          method vvdec : Cil.varinfo -> Cil.varinfo Cil.visitAction
          method vvrbl : Cil.varinfo -> Cil.varinfo Cil.visitAction
        end
      val expContainsDeref : Cil.exp -> 'a -> bool
      class globalFinderClass :
        bool ref ->
        object
          method queueInstr : Cil.instr list -> unit
          method unqueueInstr : unit -> Cil.instr list
          method vattr : Cil.attribute -> Cil.attribute list Cil.visitAction
          method vattrparam : Cil.attrparam -> Cil.attrparam Cil.visitAction
          method vblock : Cil.block -> Cil.block Cil.visitAction
          method vexpr : Cil.exp -> Cil.exp Cil.visitAction
          method vfunc : Cil.fundec -> Cil.fundec Cil.visitAction
          method vglob : Cil.global -> Cil.global list Cil.visitAction
          method vinit :
            Cil.varinfo -> Cil.offset -> Cil.init -> Cil.init Cil.visitAction
          method vinitoffs : Cil.offset -> Cil.offset Cil.visitAction
          method vinst : Cil.instr -> Cil.instr list Cil.visitAction
          method vlval : Cil.lval -> Cil.lval Cil.visitAction
          method voffs : Cil.offset -> Cil.offset Cil.visitAction
          method vstmt : Cil.stmt -> Cil.stmt Cil.visitAction
          method vtype : Cil.typ -> Cil.typ Cil.visitAction
          method vvdec : Cil.varinfo -> Cil.varinfo Cil.visitAction
          method vvrbl : Cil.varinfo -> Cil.varinfo Cil.visitAction
        end
      val expContainsGlobal : Cil.exp -> bool
      class aliasFinderClass :
        Cil.exp ->
        bool ref ->
        object
          method queueInstr : Cil.instr list -> unit
          method unqueueInstr : unit -> Cil.instr list
          method vattr : Cil.attribute -> Cil.attribute list Cil.visitAction
          method vattrparam : Cil.attrparam -> Cil.attrparam Cil.visitAction
          method vblock : Cil.block -> Cil.block Cil.visitAction
          method vexpr : Cil.exp -> Cil.exp Cil.visitAction
          method vfunc : Cil.fundec -> Cil.fundec Cil.visitAction
          method vglob : Cil.global -> Cil.global list Cil.visitAction
          method vinit :
            Cil.varinfo -> Cil.offset -> Cil.init -> Cil.init Cil.visitAction
          method vinitoffs : Cil.offset -> Cil.offset Cil.visitAction
          method vinst : Cil.instr -> Cil.instr list Cil.visitAction
          method vlval : Cil.lval -> Cil.lval Cil.visitAction
          method voffs : Cil.offset -> Cil.offset Cil.visitAction
          method vstmt : Cil.stmt -> Cil.stmt Cil.visitAction
          method vtype : Cil.typ -> Cil.typ Cil.visitAction
          method vvdec : Cil.varinfo -> Cil.varinfo Cil.visitAction
          method vvrbl : Cil.varinfo -> Cil.varinfo Cil.visitAction
        end
      val expHasAlias : Cil.exp -> Cil.exp -> bool
      val makeFormalPreds : Cil.varinfo list -> Cil.exp list -> Cil.exp list
      val makeReturnPreds :
        Cil.varinfo option ->
        Cil.varinfo list ->
        Cil.varinfo list -> Cil.exp list -> Cil.exp list -> Cil.exp list
      val funSigHash : funcSig IH.t
      class funcSigMakerClass :
        object
          method queueInstr : Cil.instr list -> unit
          method unqueueInstr : unit -> Cil.instr list
          method vattr : Cil.attribute -> Cil.attribute list Cil.visitAction
          method vattrparam : Cil.attrparam -> Cil.attrparam Cil.visitAction
          method vblock : Cil.block -> Cil.block Cil.visitAction
          method vexpr : Cil.exp -> Cil.exp Cil.visitAction
          method vfunc : Cil.fundec -> Cil.fundec Cil.visitAction
          method vglob : Cil.global -> Cil.global list Cil.visitAction
          method vinit :
            Cil.varinfo -> Cil.offset -> Cil.init -> Cil.init Cil.visitAction
          method vinitoffs : Cil.offset -> Cil.offset Cil.visitAction
          method vinst : Cil.instr -> Cil.instr list Cil.visitAction
          method vlval : Cil.lval -> Cil.lval Cil.visitAction
          method voffs : Cil.offset -> Cil.offset Cil.visitAction
          method vstmt : Cil.stmt -> Cil.stmt Cil.visitAction
          method vtype : Cil.typ -> Cil.typ Cil.visitAction
          method vvdec : Cil.varinfo -> Cil.varinfo Cil.visitAction
          method vvrbl : Cil.varinfo -> Cil.varinfo Cil.visitAction
        end
      val makeFunctionSigs : Cil.file -> funcSig IH.t
      val h_equals : 'a IH.t -> 'a IH.t -> bool
      val hl_equals : 'a IH.t list -> 'a IH.t list -> bool
      val h_combine : boolLat IH.t -> boolLat IH.t -> boolLat IH.t
      val hl_combine :
        boolLat IH.t list -> boolLat IH.t list -> boolLat IH.t list
      val substitute : Cil.exp -> Cil.lval -> Cil.exp -> Cil.exp
      val weakestPrecondition : Cil.instr -> Cil.exp -> Cil.exp option
      val getPred : context -> int -> Cil.exp
      val buildPreAndTest :
        context ->
        boolLat IH.t ->
        boolLat IH.t ->
        Cil.exp list -> bool -> Cil.instr option -> boolLat IH.t
      val handleSetInstr :
        context ->
        Cil.exp list ->
        boolLat IH.t -> Cil.instr -> boolLat IH.t -> boolLat IH.t
      val handleCallInstr :
        context ->
        Cil.exp list ->
        boolLat IH.t -> Cil.instr -> boolLat IH.t -> boolLat IH.t
      val fixForExternCall :
        context ->
        boolLat IH.t -> Cil.lval option -> Cil.exp list -> boolLat IH.t
      val handleIl : context -> Cil.instr list -> stmtState -> stmtState
      val handleStmt : context -> Cil.stmt -> stmtState -> stmtState
      val handleBranch : context -> Cil.exp -> stmtState -> stmtState
      val listInit : int -> 'a -> 'a list
      val currentContext : context
      module PredFlow :
        sig
          val name : string
          val debug : bool ref
          type t = stmtState
          val copy : stmtState -> stmtState
          val stmtStartData : t IH.t
          val pretty : unit -> stmtState -> Pretty.doc
          val computeFirstPredecessor : Cil.stmt -> stmtState -> stmtState
          val combinePredecessors :
            Cil.stmt -> old:t -> t -> stmtState option
          val doInstr : 'a -> 'b -> 'c DF.action
          val doStmt : Cil.stmt -> stmtState -> stmtState DF.stmtaction
          val doGuard : Cil.exp -> stmtState -> stmtState DF.guardaction
          val filterStmt : 'a -> bool
        end
      module PA : sig val compute : Cil.stmt list -> unit end
      val registerFile : Cil.file -> unit
      val makePreds : ExpIntHash.key list -> unit
      val makeAllBottom : Cil.exp IH.t -> boolLat IH.t
      val analyze : Cil.fundec -> unit
      val getPAs : int -> PredFlow.t option
      class paVisitorClass :
        object
          val mutable cur_pa_dat : boolLat IH.t option
          val mutable pa_dat_lst : boolLat IH.t list
          val mutable sid : int
          method get_cur_dat : unit -> boolLat IH.t option
          method queueInstr : Cil.instr list -> unit
          method unqueueInstr : unit -> Cil.instr list
          method vattr : Cil.attribute -> Cil.attribute list Cil.visitAction
          method vattrparam : Cil.attrparam -> Cil.attrparam Cil.visitAction
          method vblock : Cil.block -> Cil.block Cil.visitAction
          method vexpr : Cil.exp -> Cil.exp Cil.visitAction
          method vfunc : Cil.fundec -> Cil.fundec Cil.visitAction
          method vglob : Cil.global -> Cil.global list Cil.visitAction
          method vinit :
            Cil.varinfo -> Cil.offset -> Cil.init -> Cil.init Cil.visitAction
          method vinitoffs : Cil.offset -> Cil.offset Cil.visitAction
          method vinst : Cil.instr -> Cil.instr list Cil.visitAction
          method vlval : Cil.lval -> Cil.lval Cil.visitAction
          method voffs : Cil.offset -> Cil.offset Cil.visitAction
          method vstmt : Cil.stmt -> Cil.stmt Cil.visitAction
          method vtype : Cil.typ -> Cil.typ Cil.visitAction
          method vvdec : Cil.varinfo -> Cil.varinfo Cil.visitAction
          method vvrbl : Cil.varinfo -> Cil.varinfo Cil.visitAction
        end
      val query : boolLat IH.t -> ExpIntHash.key -> boolLat
    end
