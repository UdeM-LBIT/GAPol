from .evolve.GenomeBase import GenomeBase
from collections import Counter, defaultdict as ddict
import numpy as np
import random
import math
import hashlib
from functools import partial
from itertools import permutations, product
from ..TreeLib import TreeClass, TreeUtils
from heapq import heappushpop, heappush


class BranchRep:
    # BranchRep(node, partition, isinternal)
    def __init__(self, node, partition, nodetype):
        self.node = node
        self.node.sort_descendants(attr="species")

        self.in_node, self.out_node = partition
        self.part1 = [x.species for x in self.in_node]
        self.part2 = [x.species for x in self.out_node]        
        self.nodetype =  nodetype
    
    def get_hash(self, partition):
        return hashlib.sha384(",".join(sorted(partition))).hexdigest()

    def _get_spec_nw(self):
        new_t = self.node.copy()
        for node in new_t:
            node.name = node.species
        return new_t.write(format=9)

    def __hash__(self):
        hashp = self.get_hash(self.part1) + self.get_hash(self.part2)
        return hash(hashlib.sha384(self._get_spec_nw()).hexdigest() + hashp)
    

    def __eq__(self, other):
        same_hash = self.__hash__() == other.__hash__()
        p1 = (sorted(self.part1), sorted(self.part2))
        p2 = (sorted(other.part1), sorted(other.part2))
        return same_hash and self.nodetype == other.nodetype and (p1 == p2 or p1 == p2[::-1])


class Utils:
    
    @staticmethod
    def _enumerate_permutation(gmap):
        perm_keeper =  ddict(list)
        for k,v in gmap.items():
            perm_keeper[k] = [x for x in permutations(v)]
        return perm_keeper

    @staticmethod
    def reroot(genome):
        genome.tree = next(genome.tree.edge_reroot())
        return genome
    
    @staticmethod
    def best_tree_finder(trees, raxmlmod, gmap, ntrees, timelimit=None):
        best_trees = []
        perm_keeper = Utils._enumerate_permutation(gmap)
        keylist =  dict((x,y) for y, x in enumerate (perm_keeper.keys()))
        product_list = product(*perm_keeper.values())
        i = 0 
        start_time = time.time()
        stop = False
        for plabel in product_list:
            if not stop:
                for t in trees:
                    ind = [0 for ckey in keylist]
                    tcop = t.copy()
                    for node in tcop:
                        spec_pos = keylist[node.name]
                        node.name =  plabel[spec_pos][ind[spec_pos]]
                        ind[spec_pos] += 1
                    score, _ = raxmlmod.optimize_model(tcop)
                    i += 1
                    print("Trees %d, score : %f" %(i, score))
                    if ntrees<0 or len(best_trees) <= ntrees:
                        heappush(best_trees, (score, tcop))
                    else:
                        # here push the new item then pop the tree with 
                        # smallest value from it 
                        heappushpop(best_trees, (score, tcop))
                    if timelimit and cur_time - start_time > timelimit: 
                        stop = True
                        break
        return best_trees

    @staticmethod
    def _skeletoncompare(tree1, tree2):
        
        if tree1 is None and tree2 is None:
            return True

        elif tree1 is None or tree2 is None:
            return False

        elif tree1.name != tree2.name or tree1.species!= tree2.species:
            return False

        c11, c12 = tree1.get_children()
        c21, c22 = tree2.get_children() 
        return (_skeletoncompare(c11, c21) and _skeletoncompare(c12, c22)) or (_skeletoncompare(c11, c22) and _skeletoncompare(c12, c2))

    @staticmethod
    def treecompare(tree1, tree2, structonly=True):
        if not structonly:
            rf = tree1.robinson_foulds(tree2)
            return rf[0] == 0
        else:            
            return _skeletoncompare(tree1, tree2)
                            
    @staticmethod
    def shuffle_map(gmap):
        for k,v in gmap.items():
            np.random.shuffle(v)
        return gmap


    @staticmethod
    def initialize(genome, **args):
        gmap = Utils.shuffle_map(args["gmap"])
        pos = {}
        for node in genome.tree:
            node.add_features(species=node.name)
            pos[node.species] = pos.get(node.species, 0)
            node.name =  gmap[node.species][pos[node.species]]
            pos[node.species] += 1
    

    @staticmethod
    def iter_partition(tree):
        for node in tree.iter_descendants("levelorder"):
            leafset1 = set(node.get_leaves())
            leafset2 = set(tree.get_leaves()) - leafset1
            if(not node.up.is_root()):
                yield node, (leafset1, leafset2), 1-node.is_leaf()


    @staticmethod
    def two_step_branch_selection(candbranches, prob):
        # this is the probability of choosing 
        # internal branch over leaves
        internal_or_leaf = np.random.choice([1,0], p=[prob, 1-prob])
        new_cands = [x for x in candbranches if x[0].nodetype == internal_or_leaf]
        # if it's empty, then the list only contains compatible leaves
        # in that case, just selected a random branch
        if not new_cands:
            new_cands = candbranches     
        selected_branch = random.choice(new_cands)
        return selected_branch
    

    @staticmethod
    def find_and_swap(br, g1, g2):
        branch, nodelist = br
        g1_list = []
        g2_list = []
        for x  in nodelist:
            if x[-1] == 0:
                g1_list.append(x[0])
            else:
                g2_list.append(x[0])
        #print g1_list
        #print g2_list
        g1swap = g1_list[0]
        g2swap = g2_list[0]
        g1_parent = g1swap.up
        g2_parent = g2swap.up

        # fix problem due to same name multiple time

        swap_spec, g1_nname = zip(*[(x.species, x.name) for x in g1swap])
        g2_nname = set([x.name for x in g2swap])
        g1_nname = set(g1_nname)
        #print g1swap.robinson_foulds(g2swap)
        if g2_nname^g1_nname:
            # attempt to correct repeated leaves
            g1_swapper = ddict(list)
            g2_swapper = ddict(list)
            not_in_g1_swapper = set(g1.tree) - set(g1swap)
            for n in not_in_g1_swapper:
                g1_swapper[n.species].append(n)

            not_in_g2_swapper = list(set(g2.tree) - set(g2swap))
            for n in not_in_g2_swapper:
                g2_swapper[n.species].append(n)

            for spec in set(swap_spec):
                tmp1_n = set([x.name for x in g1_swapper[spec]])
                tmp2_n = set([x.name for x in g2_swapper[spec]])
                tmp1_n, tmp2_n = tmp2_n - tmp1_n, tmp1_n - tmp2_n  
                
                for n in g1_swapper[spec]:
                    if n.name in g2_nname:
                        n.name = set.pop(tmp1_n)
                for n in g2_swapper[spec]:
                    if n.name in g1_nname:
                        n.name = set.pop(tmp2_n)     
        
        g2_parent.add_child(g1swap.detach())
        g1_parent.add_child(g2swap.detach())
        return g1, g2
        
        
    @staticmethod
    def permute_seq(genome, spec):
        nlist = genome.tree.search_nodes(species=spec)
        if len(nlist)>1:
            n1, n2 = np.random.choice(nlist, 2, replace=False)
            n1.name, n2.name = n2.name, n1.name            
         

    @staticmethod
    def branch_is_valid(branch, gholder):
        # branch should be present at both genome
        # parent trees
        gholder_type = set([x[-1] for x in gholder])
        if len(gholder_type) < 2:
            return False
        else:
            # branch should have the same count of leaves of same 
            # species under it
            # counter for species count at leaves
            ln = [Counter([leaf.species for leaf in v[0]]) for v in gholder]
            return all(x==ln[0] for x in ln)
        

    @staticmethod
    def get_candtransfer_branches(genome):

        candlist = genome.tree.get_descendants()
        cand =  random.choice(candlist)
        incomp_cand = random.choice(list(cand.get_incomparable_list()))
        return (cand.up, cand), (incomp_cand.up, incomp_cand)


    @staticmethod
    def is_suitable(donor, receiver):
        # This should be used to decide whether or not 
        # the current proposed transfer should be considered
        # 
        # Here we supposed that it's if donor and receiver are 
        # not sister. Could find better way to improve this though
        return donor[0] != receiver[0]

    @staticmethod
    def compute_height(node, hmap={}):
        res = 1
        if node.is_leaf():
            res = 1
        else:
            res = 1 + max([hmap.get(x, Utils.compute_height(x, hmap)[0]) for x in node.get_children()])
        hmap[node] = res
        return res, hmap


    @staticmethod    
    def graftTreeAt(subtree, node):
        if not node.edge_exist(node.up):
            raise ValueError("Edge not found")
        else:
            nodeup = node.up
            node.detach()
            subtree.detach()
            newNode = TreeClass()  
            newNode.add_child(subtree)
            newNode.add_child(node)
            if nodeup:
                nodeup.add_child(newNode)
            else:
                nodeup = newNode
            return nodeup.get_tree_root()

    @staticmethod
    def no_recon_crossover(gdad, gmom):
        # we are going to  assume that this is done ramdomly
        gchild1 =  gdad.clone()
        gchild2 =  gmom.clone()
        tmp1 =  gchild1.tree.copy()
        tmp2 =  gchild2.tree.copy()
        # select a random internal branch and swap topology with the one of the second parent
        internal_node = tmp1.get_tree_root().get_descendants()
        #hmap = {}
        #in_prob = []
        #for inode in internal_node:
        #    h, hmap = Utils.compute_height(inode, hmap)
        #    in_prob.append(h)
        #in_prob = np.array(in_prob, dtype='float')
        #in_prob = in_prob/np.sum(in_prob)
        subtree1 = np.random.choice(internal_node)#,  p=in_prob)
        lset1 = subtree1.get_leaf_names()
        for l in gchild2.tree:
            if l.name in lset1:
                l.delete()
        gchild2.tree.delete_single_child_internal(enable_root=True)
        selected_node = np.random.choice([x for x in gchild2.tree.traverse()])
            
        gchild2.tree = Utils.graftTreeAt(subtree1, selected_node)
        gchild2.tree.delete_single_child_internal(enable_root=True)
        assert len(gchild1.tree) == len(gchild2.tree) == len(gdad.tree), "NOOOOOOOOOOOOO"

        # same as above but for second tree
        internal_node = tmp2.get_tree_root().get_descendants()#get_internal_node()
        #hmap = {}
        #in_prob = []
        #for inode in internal_node:
        #    h, hmap = Utils.compute_height(inode, hmap)
        #    in_prob.append(h)
        #in_prob = np.array(in_prob, dtype='float')
        #in_prob = in_prob/np.sum(in_prob)
        subtree2 = np.random.choice(internal_node)#,  p=in_prob)
        lset2 = subtree2.get_leaf_names()
        for l in gchild1.tree:
            if l.name in lset2:
                l.delete()
        gchild1.tree.delete_single_child_internal(enable_root=True)
        selected_node = np.random.choice([x for x in gchild1.tree.traverse()])
        gchild1.tree = Utils.graftTreeAt(subtree2, selected_node)

        gchild1.tree.delete_single_child_internal(enable_root=True)
        assert len(gchild1.tree) == len(gchild2.tree) == len(gdad.tree), "NOOOOOOOOOOOOO"
        return gchild1, gchild2


    @staticmethod
    def SPR_move(tree, donor, receiver):
        # detach 
        intruit =  donor[1].detach()
        donor[0].delete()
        # graft to new branch
        truedesc = receiver[1].detach()
        new_node = TreeClass()
        new_node.add_child(intruit)
        new_node.add_child(truedesc)
        receiver[0].add_child(new_node)


    @staticmethod
    def performSPR(genome):
        # donnor and receiver are branches
        donor, receiver  = Utils.get_candtransfer_branches(genome)
        # can't give or receive at root
        if donor[0].is_root() or receiver[1].is_root():
            return genome
        elif Utils.is_suitable(donor, receiver):
            Utils.SPR_move(genome.tree, donor, receiver)
            genome.set_done_transfer()
        return genome


    @staticmethod
    def crossover(obj, **args):

        if args['mom'].reconcile:
            return Utils.no_recon_crossover(args['dad'], args['mom'])
        else:
            return Utils.cost_preserve_crossover(args['dad'], args['mom'])


    @staticmethod
    def cost_preserve_crossover(gdad, gmom):
        genome1 = gdad.clone()
        genome2 = gmom.clone()
        prob = max(genome1.intbrnp, genome2.intbrnp)
        current_dict = ddict(list)
        for (gind, g) in enumerate([genome1, genome2]):
            for node, partition, isinternal in Utils.iter_partition(g.tree):
                brnch = BranchRep(node, partition, isinternal)
                current_dict[brnch].append((node, gind))
        candidates = [(k,v) for k,v in current_dict.items() if Utils.branch_is_valid(k,v)]
        selected_branch = Utils.two_step_branch_selection(candidates, prob)

        return Utils.find_and_swap(selected_branch, genome1, genome2)
        
    
    @staticmethod
    def mutate(genome, **args):
        n_mutation = 0
        nspec = genome.get_spec_len()
        av_mutation =  args["pmut"]*nspec
        engine = args["ga_engine"]
        spec_list = genome.spcount.keys()
        # here multiple mutations are wanted
        # we do exactly av_mutation 
        if engine.getParam('fastconv', False) and av_mutation >1.0:
            for i in range(int(np.ceil(av_mutation))):
                #crossover choose random species and mutate
                # or perform SPR randomly
                if np.random.rand() > 0.5:
                    spec = np.random.choice(spec_list)
                    Utils.permute_seq(genome, spec)
                else:
                    Utils.performSPR(genome)
                n_mutation += 1
        
        # just do one mutation, so no fastconv
        else:
            probmut = np.random.rand()  
            if probmut <= args['pmut']:
                if genome.reconcile:
                    # choose between SPR, reroot, edge and dlt
                    selection = engine.recparam.select_event(genome)
                    if selection=='ROOT':
                        Utils.reroot(genome)
                    if selection=='DTL':
                        genome.dtlrates.mutate()
                    elif selection=="EDGE":
                        genome.erates.mutate()
                    else:
                        Utils.performSPR(genome)
                else:
                    spec = np.random.choice(spec_list)
                    Utils.permute_seq(genome, spec)
                n_mutation +=1
            
        return n_mutation

    @staticmethod
    def evaluate(genome, **args):
        raxmlmodel = genome.model
        
        score, tree = raxmlmodel.optimize_model(genome.tree, expect_tree=True, **args)
        # here we will updtate genome data
        if tree:
            genome.update_tree(tree[0])
        if isinstance(score, list):
            return -score[0]
        return -score
    
    @staticmethod
    def costEvaluate(genome, **args):
        engine =  args['ga_engine']
        return engine.recparam.computeRecCost(genome, **args)
    
    @staticmethod
    def bulk_evaluate(genomes, **args):
        raxmlmodel = args.get('model', genomes[0].model)
        treelist = [g.tree for g in genomes]
        scores, _ = raxmlmodel.optimize_model(treelist, **args)
        if not len(scores)==len(treelist):
            print("Evaluation failed")
            print len(scores), ' <==score vs treelist===> ', len(treelist)
            print scores
            raise ValueError("Something went wrong, see ==> %s"%raxmlmodel.title)

        return [-x for x in scores]


class GPolySolver(GenomeBase):
    
    gmap = {}
    reversemap = {}
    reconcile = True
    def __init__(self, tree, model, dtlrates, erates, intbrnp=0.95, gmap={}, is_init=False):
        GenomeBase.__init__(self)
        self.tree =  tree
        #self.skeleton = self._get_sekeleton()
        self.model = model
        self.intbrnp = intbrnp
        self.is_init = is_init
        self._done_transfer = False
        if gmap:
            self.setGeneMap(gmap)
        self.spcount = None
        self.dtlrates = dtlrates
        self.erates = erates
        try:
            self.spcount =  Counter(tree.get_leaf_names())
        except:
            pass
        self.initializator.set(Utils.initialize)
        self.mutator.set(Utils.mutate)
        
        self.evaluator.set(Utils.evaluate)
        if GPolySolver.reconcile:
            self.evaluator.add(Utils.costEvaluate)

        self.crossover.set(Utils.crossover)

    def get_spec_len(self):
        return len(self.spcount.keys())
    
    def set_done_transfer(self):
        self._done_transfer = True

    def has_undergo_transfer(self):
        return self._done_transfer

    def _get_skeleton(self, specmap):
        skeleton = self.tree.copy()
        if specmap and self.is_init:
            for leaf in skeleton:
                for s, genes in specmap.items():
                    if leaf.name in genes:
                        leaf.name  = s
                        break
        return skeleton

    def update_tree(self, t):
        outgroup = None
        try:
            leaf_names = self.tree.get_child_at(0).get_leaf_names()
            if len(leaf_names) > 1:
                outgroup = t.get_common_ancestor(*leaf_names)
            else:
                outgroup = t&leaf_names[0]
            t.set_outgroup(outgroup)

        except:
            leaf_names = self.tree.get_child_at(1).get_leaf_names()
            if len(leaf_names) > 1:
                outgroup = t.get_common_ancestor(leaf_names)
            else:
                outgroup = t&leaf_names[0]
            t.set_outgroup(outgroup)
            
        for node in self.tree.traverse():
            for feat in node.features:
                if feat not in ['dist','name']:
                    if node.is_leaf():
                        (t&node.name).add_feature(feat, node.get_feature(feat))
                    else:
                        t.get_common_ancestor(node.get_leaf_names()).add_feature(feat, node.get_feature(feat))
        self.tree = t

    def get_tree_with_br(self):
        score, tree = self.model.optimize_model(self.tree, expect_tree=True, forcelog=True)
        if tree:
            self.update_tree(tree[0])
        return self.tree

    @classmethod
    def setGeneMap(clc, val):
        clc.gmap = val
        clc.reversemap = dict((gname, spname) for spname in clc.gmap.keys() for gname in clc.gmap[spname])

    @classmethod
    def setReconcile(clc, recparam):
        clc.reconcile = (recparam is not None)

    def initialize(self, **args):
        """ Called to initialize genome
        :param args: this parameters will be passed to the initializator
        """
        args['gmap'] = GPolySolver.gmap
        if not self.is_init:
            for it in self.initializator.applyFunctions(self, **args):
                pass
        else:
            for spec, names in GPolySolver.gmap.items(): 
                for name in names:
                    (self.tree&name).add_features(species=spec)

        self.is_init = True


    def copy(self, g):
        """ Copy the current GenomeBase to 'g'
        :param g: the destination genome
        .. note:: If you are planning to create a new chromosome representation, you
                **must** implement this method on your class.
        """
        GenomeBase.copy(self, g)
        g.tree =  self.tree.copy()
        g.dtlrates = self.dtlrates.clone()
        g.erates = self.erates.clone()
        g.spcount = self.spcount
        g.intbrnp = self.intbrnp
        g.model = self.model
        g.is_init = self.is_init
        g._done_transfer = False
    

    def clone(self):
        """ Clone this GenomeBase
        :rtype: the clone genome
        .. note:: If you are planning to create a new chromosome representation, you
            **must** implement this method on your class.
        """
        newcopy = GPolySolver(None, None,None, None)
        self.copy(newcopy)
        return newcopy

    def set_species(self):
        for node in self.tree:
            if not node.has_feature("species"):
                node.add_features(species=self.reversemap[node.name])
    
    def __eq__(self, other):
        """Comparison of GenomeBase instance"""
        same_score = False
        if self.score and other.score:
            if isinstance(self.score, list) and isinstance(other.score, list) and len(self.score) == len(other.score):
                same_score = all(["%.5f"%s == "%.5f"%other.score[i] for i,s in enumerate(self.score)])
            else:
                same_score = (self.score == other.score)
        rf = self.tree.robinson_foulds(other.tree)
        return rf[0] == 0 and (self.model == other.model) and same_score 