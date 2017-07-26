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
module UD :
  sig
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
    module VS :
      sig
        type elt = Cil.varinfo
        type t = Usedef.VS.t
        val empty : t
        val is_empty : t -> bool
        val mem : elt -> t -> bool
        val add : elt -> t -> t
        val singleton : elt -> t
        val remove : elt -> t -> t
        val union : t -> t -> t
        val inter : t -> t -> t
        val diff : t -> t -> t
        val compare : t -> t -> int
        val equal : t -> t -> bool
        val subset : t -> t -> bool
        val iter : (elt -> unit) -> t -> unit
        val fold : (elt -> 'a -> 'a) -> t -> 'a -> 'a
        val for_all : (elt -> bool) -> t -> bool
        val exists : (elt -> bool) -> t -> bool
        val filter : (elt -> bool) -> t -> t
        val partition : (elt -> bool) -> t -> t * t
        val cardinal : t -> int
        val elements : t -> elt list
        val min_elt : t -> elt
        val max_elt : t -> elt
        val choose : t -> elt
        val split : elt -> t -> t * bool * t
      end
    val getUseDefFunctionRef :
      (Cil.exp -> Cil.exp list -> VS.t * VS.t * Cil.exp list) ref
    val considerVariableUse : (VS.elt -> bool) ref
    val considerVariableDef : (VS.elt -> bool) ref
    val considerVariableAddrOfAsUse : (VS.elt -> bool) ref
    val considerVariableAddrOfAsDef : (VS.elt -> bool) ref
    val extraUsesOfExpr : (Cil.exp -> VS.t) ref
    val onlyNoOffsetsAreDefs : bool ref
    val ignoreSizeof : bool ref
    val varUsed : VS.t ref
    val varDefs : VS.t ref
    class useDefVisitorClass : Cil.cilVisitor
    val useDefVisitor : useDefVisitorClass
    val computeUseExp : ?acc:VS.t -> Cil.exp -> VS.t
    val computeUseDefInstr :
      ?acc_used:VS.t -> ?acc_defs:VS.t -> Cil.instr -> VS.t * VS.t
    val computeUseDefStmtKind :
      ?acc_used:VS.t -> ?acc_defs:VS.t -> Cil.stmtkind -> VS.t * VS.t
    val computeDeepUseDefStmtKind :
      ?acc_used:VS.t -> ?acc_defs:VS.t -> Cil.stmtkind -> VS.t * VS.t
    val computeUseLocalTypes : ?acc_used:VS.t -> Cil.fundec -> VS.t
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
val doTime : bool ref
val time : string -> ('a -> 'b) -> 'a -> 'b
val ignore_inst : (Cil.instr -> bool) ref
val ignore_call : (Cil.instr -> bool) ref
val registerIgnoreInst : (Cil.instr -> bool) -> unit
val registerIgnoreCall : (Cil.instr -> bool) -> unit
val eh_equals : Cil.exp IH.t -> Cil.exp IH.t -> bool
val eh_pretty : unit -> Cil.exp IH.t -> Pretty.doc
val eh_combine : Cil.exp IH.t -> Cil.exp IH.t -> Cil.exp IH.t
class memReadOrAddrOfFinderClass :
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
val exp_has_mem_read : Cil.exp -> bool
val eh_kill_mem : Cil.exp IH.t -> unit
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
val exp_has_vi : Cil.varinfo -> Cil.exp -> bool
val eh_kill_vi : Cil.exp IH.t -> Cil.varinfo -> unit
class lvalFinderClass :
  Cil.lval ->
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
val exp_has_lval : Cil.lval -> Cil.exp -> bool
val eh_kill_lval : Cil.exp IH.t -> Cil.lval -> unit
class volatileFinderClass :
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
val exp_is_volatile : Cil.exp -> bool
val varHash : Cil.varinfo IH.t
val eh_kill_addrof_or_global : 'a IH.t -> unit
val eh_handle_inst : Cil.instr -> Cil.exp IH.t -> Cil.exp IH.t
module AvailableExps :
  sig
    val name : string
    val debug : bool ref
    type t = Cil.exp IH.t
    val copy : 'a IH.t -> 'a IH.t
    val stmtStartData : t IH.t
    val pretty : unit -> Cil.exp IH.t -> Pretty.doc
    val computeFirstPredecessor : 'a -> 'b -> 'b
    val combinePredecessors : Cil.stmt -> old:t -> t -> Cil.exp IH.t option
    val doInstr : Cil.instr -> 'a -> Cil.exp IH.t DF.action
    val doStmt : 'a -> 'b -> 'c DF.stmtaction
    val doGuard : 'a -> 'b -> 'c DF.guardaction
    val filterStmt : 'a -> bool
  end
module AE : sig val compute : Cil.stmt list -> unit end
class varHashMakerClass :
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
val varHashMaker : varHashMakerClass
val make_var_hash : Cil.fundec -> unit
val computeAEs : Cil.fundec -> unit
val getAEs : int -> AvailableExps.t option
val instrAEs :
  Cil.instr list -> 'a -> Cil.exp IH.t -> 'b -> Cil.exp IH.t list
class aeVisitorClass :
  object
    val mutable ae_dat_lst : Cil.exp IH.t list
    val mutable cur_ae_dat : Cil.exp IH.t option
    val mutable sid : int
    method get_cur_eh : unit -> AvailableExps.t option
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
