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
module L :
  sig
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
    val debug : bool ref
    val ignore_inst : (Cil.instr -> bool) ref
    val ignore_call : (Cil.instr -> bool) ref
    val registerIgnoreInst : (Cil.instr -> bool) -> unit
    val registerIgnoreCall : (Cil.instr -> bool) -> unit
    val live_label : String.t ref
    val live_func : String.t ref
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
    val debug_print : unit -> VS.t -> Pretty.doc
    val min_print : unit -> VS.t -> Pretty.doc
    val printer : (unit -> VS.t -> Pretty.doc) ref
    module LiveFlow :
      sig
        val name : string
        val debug : bool ref
        type t = VS.t
        val pretty : unit -> VS.t -> Pretty.doc
        val stmtStartData : t IH.t
        val funcExitData : VS.t
        val combineStmtStartData : Cil.stmt -> old:t -> t -> VS.t option
        val combineSuccessors : VS.t -> VS.t -> VS.t
        val doStmt : Cil.stmt -> VS.t DF.action
        val doInstr : Cil.instr -> 'a -> VS.t DF.action
        val filterStmt : 'a -> 'b -> bool
      end
    module L : sig val compute : Cil.stmt list -> unit end
    val all_stmts : Cil.stmt list ref
    class nullAdderClass :
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
    val null_adder : Cil.fundec -> Cil.stmt list
    val computeLiveness : Cil.fundec -> unit
    val getLiveSet : int -> LiveFlow.t option
    val getLiveness : Cil.stmt -> LiveFlow.t
    val getPostLiveness : Cil.stmt -> LiveFlow.t
    val instrLiveness :
      Cil.instr list -> Cil.stmt -> VS.t -> bool -> VS.t list
    class livenessVisitorClass :
      bool ->
      object
        val mutable cur_liv_dat : VS.t option
        val mutable liv_dat_lst : VS.t list
        val mutable sid : int
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
    class deadnessVisitorClass :
      object
        val mutable cur_liv_dat : VS.t option
        val mutable liv_dat_lst : VS.t list
        val mutable post_dead_vars : VS.t
        val mutable post_live_vars : VS.t
        val mutable sid : int
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
    val print_everything : unit -> unit
    val match_label : Cil.label -> bool
    class doFeatureClass :
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
    val do_live_feature : Cil.file -> unit
    val feature : Cil.featureDescr
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
val debug_fn : string ref
val doTime : bool ref
val time : string -> ('a -> 'b) -> 'a -> 'b
module IOS :
  sig
    type elt = int option
    type t
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
val debug : bool ref
val ih_inter : 'a IH.t -> 'b IH.t -> 'a IH.t
val ih_union : 'a IH.t -> 'a IH.t -> 'a IH.t
val iosh_singleton_lookup : IOS.t IH.t -> Cil.varinfo -> IOS.elt
val iosh_lookup : 'a IH.t -> Cil.varinfo -> 'a option
val iosh_defId_find : IOS.t IH.t -> int -> int option
val iosh_combine : IOS.t IH.t -> IOS.t IH.t -> IOS.t IH.t
val iosh_equals : IOS.t IH.t -> IOS.t IH.t -> bool
val iosh_replace : IOS.t IH.t -> int -> Cil.varinfo -> unit
val iosh_filter_dead : 'a -> 'b -> 'a
val proc_defs : UD.VS.t -> IOS.t IH.t -> (unit -> int) -> unit
val idMaker : unit -> int -> unit -> int
val iRDsHtbl : (int * bool, (unit * int * IOS.t IH.t) list) Hashtbl.t
val instrRDs :
  Cil.instr list ->
  int -> 'a * int * IOS.t IH.t -> bool -> (unit * int * IOS.t IH.t) list
type rhs = RDExp of Cil.exp | RDCall of Cil.instr
val rhsHtbl : (rhs * int * IOS.t IH.t) option IH.t
val getDefRhs :
  Cil.stmt IH.t ->
  ('a * int * IOS.t IH.t) IH.t -> int -> (rhs * int * IOS.t IH.t) option
val prettyprint :
  Cil.stmt IH.t ->
  ('a * int * IOS.t IH.t) IH.t -> unit -> 'b * 'c * IOS.t IH.t -> Pretty.doc
module ReachingDef :
  sig
    val name : string
    val debug : bool ref
    val mayReach : bool ref
    type t = unit * int * IOS.t IH.t
    val copy : 'a * 'b * 'c IH.t -> unit * 'b * 'c IH.t
    val stmtStartData : (unit * int * IOS.t IH.t) IH.t
    val defIdStmtHash : Cil.stmt IH.t
    val sidStmtHash : Cil.stmt IH.t
    val pretty : unit -> unit * int * IOS.t IH.t -> Pretty.doc
    val nextDefId : int ref
    val num_defs : Cil.stmt -> int
    val computeFirstPredecessor :
      Cil.stmt -> 'a * int * 'b IH.t -> unit * int * 'b IH.t
    val combinePredecessors :
      Cil.stmt -> old:t -> t -> (unit * int * IOS.t IH.t) option
    val doInstr :
      Cil.instr -> 'a * 'b * 'c -> (unit * int * IOS.t IH.t) DF.action
    val doStmt : Cil.stmt -> 'a * 'b * 'c -> (unit * 'b * 'c) DF.stmtaction
    val doGuard : 'a -> 'b -> 'c DF.guardaction
    val filterStmt : 'a -> bool
  end
module RD : sig val compute : Cil.stmt list -> unit end
val iosh_none_fill : IOS.t IH.t -> Cil.varinfo list -> unit
val clearMemos : unit -> unit
val computeRDs : Cil.fundec -> unit
val getRDs : int -> (unit * int * IOS.t IH.t) option
val getDefIdStmt : int -> Cil.stmt option
val getStmt : int -> Cil.stmt option
val getSimpRhs : int -> rhs option
val isDefInstr : Cil.instr -> int -> bool
val ppFdec : Cil.fundec -> Pretty.doc
class rdVisitorClass :
  object
    val mutable cur_rd_dat : (unit * int * IOS.t IH.t) option
    val mutable rd_dat_lst : (unit * int * IOS.t IH.t) list
    val mutable sid : int
    method get_cur_iosh : unit -> IOS.t IH.t option
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
