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
