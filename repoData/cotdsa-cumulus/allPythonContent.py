__FILENAME__ = CFStack
import logging
import simplejson
from boto import cloudformation

class CFStack:
    def __init__(self, mega_stack_name, name, params, template_name, region, sns_topic_arn, tags = None, depends_on = None):
        self.logger = logging.getLogger(__name__)
        if mega_stack_name == name:
            self.cf_stack_name = name
        else:
            self.cf_stack_name = "%s-%s" % (mega_stack_name, name)
        self.mega_stack_name = mega_stack_name
        self.name = name
        self.yaml_params = params
        self.params = {}
        self.template_name = template_name
        self.template_body = ''
        if depends_on is None:
            self.depends_on = None
        else:
            self.depends_on = []
            for dep in depends_on:
                if dep == mega_stack_name:
                    self.depends_on.append(dep)
                else:
                    self.depends_on.append("%s-%s" % (mega_stack_name, dep))
        self.region = region
        self.sns_topic_arn = sns_topic_arn
        
        #Safer than setting default value for tags = {}
        if tags is None:
            self.tags = {}
        else:
            self.tags = tags

        try:
            open(template_name, 'r')
        except:
            self.logger.critical("Failed to open template file %s for stack %s" % (self.template_name, self.name))
            exit(1)
        if not ( type(self.yaml_params) is dict or self.yaml_params is None ):
            self.logger.critical("Parameters for stack %s must be of type dict not %s" % (self.name, type(self.yaml_params)))
            exit(1)

        self.cf_stacks = {}
        self.cf_stacks_resources = {}

    def deps_met(self, current_cf_stacks):
        if self.depends_on is None:
            return True
        else:
            for dep in self.depends_on:
                dep_met = False
                #check CF if stack we depend on has been created successfully
                for stack in current_cf_stacks:
                    if str(stack.stack_name) == dep:
                        dep_met = True
                if not dep_met:
                    return False
            return True

    def exists_in_cf(self, current_cf_stacks):
        for stack in current_cf_stacks:
            if str(stack.stack_name) == self.cf_stack_name:
                return stack
        return False

    def populate_params(self, current_cf_stacks):
        #If we have no parameters in the yaml file, set params to an empty dict and return true
        if self.yaml_params is None:
            self.params = {}
            return True
        if self.deps_met(current_cf_stacks):
            for param in self.yaml_params.keys():
                if type(self.yaml_params[param]) is dict:
                    #Static value set, so use it
                    if self.yaml_params[param].has_key('value'):
                        self.params[param] = str(self.yaml_params[param]['value'])
                    #No static value set, but if we have a source, type and variable can try getting from CF
                    elif self.yaml_params[param].has_key('source') and self.yaml_params[param].has_key('type') and self.yaml_params[param].has_key('variable'):
                        if self.yaml_params[param]['source'] == self.mega_stack_name:
                            source_stack = self.yaml_params[param]['source']
                        elif self.yaml_params[param]['source'][:1] == '-':
                            source_stack = self.yaml_params[param]['source'][1:]
                        else:
                            source_stack = "%s-%s" % (self.mega_stack_name, self.yaml_params[param]['source'])
                        self.params[param] = self.get_value_from_cf(
                                source_stack = source_stack,
                                var_type = self.yaml_params[param]['type'],
                                var_name = self.yaml_params[param]['variable']
                                )
                #If self.yaml_params[param] is a list it means there is an array of vars we need to turn into a comma sep list.
                elif type(self.yaml_params[param]) is list:
                    param_list = []
                    for item in self.yaml_params[param]:
                        if type(item) is dict:
                            #Static value set, so use it
                            if item.has_key('value'):
                                param_list.append(str(item['value']))
                            #No static value set, but if we have a source, type and variable can try getting from CF
                            elif item.has_key('source') and item.has_key('type') and item.has_key('variable'):
                                if item['source'] == self.mega_stack_name:
                                    source_stack = item['source']
                                else:
                                    source_stack = "%s-%s" % (self.mega_stack_name, item['source'])
                                param_list.append(self.get_value_from_cf(
                                    source_stack = source_stack,
                                    var_type = item['type'],
                                    var_name = item['variable']
                                    ))
                            else:
                                print "Error in yaml file, %s in parameter list for %s stack. Can't populate." % (self.yaml_params[param],self.name)
                                exit(1)
                    self.params[param] = ','.join(param_list)
            return True
        else:
            return False

    def get_cf_stack(self, stack, resources = False):
        """
        Get information on parameters, outputs and resources from a stack and cache it
        """
        if not resources:
            if not self.cf_stacks.has_key(stack):
                #We don't have this stack in the cache already so we need to pull it from CF
                cfconn = cloudformation.connect_to_region(self.region)
                self.cf_stacks[stack] = cfconn.describe_stacks(stack)[0]
            return self.cf_stacks[stack]
        else:
            if not self.cf_stacks_resources.has_key(stack):
                cfconn = cloudformation.connect_to_region(self.region)
                the_stack = self.get_cf_stack(stack = stack, resources = False)
                self.cf_stacks_resources[stack] = the_stack.list_resources()
            return self.cf_stacks_resources[stack]

    def get_value_from_cf(self, source_stack, var_type, var_name):
        """
        Get a variable from a existing cloudformation stack, var_type should be parameter, resource or output.
        If using resource, provide the logical ID and this will return the Physical ID
        """
        the_stack = self.get_cf_stack(stack = source_stack)
        if var_type == 'parameter':
            for p in the_stack.parameters:
                if str(p.key) == var_name:
                    return str(p.value)
        elif var_type == 'output':
            for o in the_stack.outputs:
                if str(o.key) == var_name:
                    return str(o.value)
        elif var_type == 'resource':
            for r in self.get_cf_stack(stack = source_stack, resources = True):
                if str(r.logical_resource_id) == var_name:
                    return str(r.physical_resource_id)
        else:
            print "Error: invalid var_type passed to get_value_from_cf, needs to be parameter, resource or output. Not: %s" % (var_type)
            exit(1)



    def get_params_tuples(self):
        tuple_list = []
        if len(self.params) > 0:
            for param in self.params.keys():
                tuple_list.append((param, self.params[param]))
        return tuple_list

    def read_template(self):
        try:
            template_file = open(self.template_name, 'r')
            template = simplejson.load(template_file)
        except Exception as e:
            print "Cannot parse %s template for stack %s. Error: %s" % (self.template_name, self.name, e)
            exit(1)
        self.template_body = simplejson.dumps(template)
        return True


    def template_uptodate(self, current_cf_stacks):
        """
        Check if stack is up to date with cloudformation.
        Returns true if template matches whats in cloudformation, false if not or stack not found.
        """
        cf_stack = self.exists_in_cf(current_cf_stacks)
        if not cf_stack:
            return False
        cf_template_dict = simplejson.loads(cf_stack.get_template()['GetTemplateResponse']['GetTemplateResult']['TemplateBody'])
        if cf_template_dict == simplejson.loads(self.template_body):
            return True
        else:
            return False

    def params_uptodate(self, current_cf_stacks):
        """
        Check if parameters in stack are up to date with Cloudformation
        """
        cf_stack = self.exists_in_cf(current_cf_stacks)
        if not cf_stack:
            return False

        #If number of params in CF and this stack obj dont match, then it needs updating
        if len(cf_stack.parameters) != len(self.params):
            self.logger.debug("New and old parameter lists are different lengths for %s" % (self.name))
            return False

        for param in cf_stack.parameters:
            #check if param in CF exists in our new parameter set,
            #if not they are differenet and need updating
            if not self.params.has_key(str(param.key)):
                self.logger.debug("New params are missing key %s that exists in CF for %s stack already." % (str(param.key), self.name))
                return False
            #if the value of parameters are different, needs updating
            if self.params[str(param.key)] != str(param.value):
                self.logger.debug("Param %s for stack %s has changed from %s to %s" % (str(param.key), self.name, str(param.value), self.params[str(param.key)]))
                return False

        #We got to the end without returning False, so must be fine.
        return True



########NEW FILE########
__FILENAME__ = MegaStack
import boto
import logging
import simplejson
import time
import yaml
import pystache
import os
from CFStack import CFStack
from boto import cloudformation

class MegaStack:
    """
    Main workder class for cumulus. Holds array of CFstack objects and does most of the calls to cloudformation API
    """
    def __init__(self, yamlFile):
        self.logger = logging.getLogger(__name__)

        #load the yaml file and turn it into a dict
        thefile = open(yamlFile, 'r')

        renderedFile = pystache.render(thefile.read(), dict(os.environ))

        self.stackDict = yaml.safe_load(renderedFile)
        #Make sure there is only one top level element in the yaml file
        if len(self.stackDict.keys()) != 1:
            self.logger.critical("Need one and only one mega stack name at the top level, found %s" % len(self.stackDict.keys()))
            exit(1)

        #How we know we only have one top element, that must be the mega stack name
        self.name = self.stackDict.keys()[0]

        #Find and set the mega stacks region. Exit if we can't find it
        if self.stackDict[self.name].has_key('region'):
            self.region = self.stackDict[self.name]['region']
        else:
            self.logger.critical("No region specified for mega stack, don't know where to build it.")
            exit(1)

        self.sns_topic_arn = self.stackDict[self.name].get('sns-topic-arn', [])
        if isinstance(self.sns_topic_arn, str): self.sns_topic_arn = [self.sns_topic_arn]
        for topic in self.sns_topic_arn:
            if topic.split(':')[3] != self.region:
                self.logger.critical("SNS Topic %s is not in the %s region." % (topic, self.region))
                exit(1)

        self.global_tags = self.stackDict[self.name].get('tags', {})
        #Array for holding CFStack objects once we create them
        self.stack_objs = []

        #Get the names of the sub stacks from the yaml file and sort in array
        self.cf_stacks = self.stackDict[self.name]['stacks'].keys()

        #Megastack holds the connection to cloudformation and list of stacks currently in our region
        #Stops us making lots of calls to cloudformation API for each stack
        try:
            self.cfconn = cloudformation.connect_to_region(self.region)
            self.cf_desc_stacks = self.cfconn.describe_stacks()
        except boto.exception.NoAuthHandlerFound as e:
            self.logger.critical("No credentials found for connecting to cloudformation: %s" % e )
            exit(1)

        #iterate through the stacks in the yaml file and create CFstack objects for them
        for stack_name in self.cf_stacks:
            the_stack = self.stackDict[self.name]['stacks'][stack_name]
            if type(the_stack) is dict:
                if the_stack.get('disable', False):
                    self.logger.warning("Stack %s is disabled by configuration directive. Skipping" % stack_name)
                    continue
                local_sns_arn = the_stack.get('sns-topic-arn', self.sns_topic_arn)
                if isinstance(local_sns_arn, str): local_sns_arn = [local_sns_arn]
                for topic in local_sns_arn:
                    if topic.split(':')[3] != self.region:
                        self.logger.critical("SNS Topic %s is not in the %s region." % (topic, self.region))
                        exit(1)
                local_tags = the_stack.get('tags', {})
                merged_tags = dict(self.global_tags.items() + local_tags.items())
                # Add static cumulus-stack tag
                merged_tags['cumulus-stack'] = self.name
                if the_stack.has_key('cf_template'):
                    self.stack_objs.append(
                        CFStack(
                            mega_stack_name=self.name,
                            name=stack_name,
                            params=the_stack['params'],
                            template_name=the_stack['cf_template'],
                            region=self.region,
                            sns_topic_arn=local_sns_arn,
                            depends_on=the_stack['depends'],
                            tags=merged_tags
                        )
                    )

    def sort_stacks_by_deps(self):
        """
        Sort the array of stack_objs so they are in dependancy order
        """
        sorted_stacks = []
        dep_graph = {}
        no_deps = []
        #Add all stacks without dependancies to no_deps
        for stack in self.stack_objs:
            if stack.depends_on is None:
                no_deps.append(stack)
            else:
                dep_graph[stack.name] = stack.depends_on[:]
        #Perform a topological sort on stacks in dep_graph
        while len(no_deps) > 0:
            stack = no_deps.pop()
            sorted_stacks.append(stack)
            for node in dep_graph.keys():
                for deps in dep_graph[node]:
                    if stack.cf_stack_name == deps:
                        dep_graph[node].remove(stack.cf_stack_name)
                        if len(dep_graph[node]) < 1:
                            for n in self.stack_objs:
                                if n.name == node:
                                    no_deps.append(n)
                            del(dep_graph[node])
        if len(dep_graph) > 0:
            self.logger.critical("Could not resolve dependancy order. Either circular dependancy or dependancy on stack not in yaml file.")
            exit(1)
        else:
            self.stack_objs = sorted_stacks
            return True

    def check(self, stack_name = None):
        """
        Checks the status of the yaml file. Displays parameters for the stacks it can.
        """
        for stack in self.stack_objs:
            if stack_name and stack.name != stack_name:
                continue
            self.logger.info("Starting check of stack %s" % stack.name)
            if not stack.populate_params(self.cf_desc_stacks):
                self.logger.info("Could not determine correct parameters for Cloudformation stack %s\n" % stack.name + 
                        "\tMost likely because stacks it depends on haven't been created yet.")
            else:
                self.logger.info("Stack %s would be created with following parameter values: %s" % (stack.cf_stack_name, stack.get_params_tuples()))
                self.logger.info("Stack %s already exists in CF: %s" % (stack.cf_stack_name, bool(stack.exists_in_cf(self.cf_desc_stacks))))

    def create(self, stack_name = None):
        """
        Create all stacks in the yaml file. Any that already exist are skipped (no attempt to update)
        """
        for stack in self.stack_objs:
            if stack_name and stack.name != stack_name:
                continue
            self.logger.info("Starting checks for creation of stack: %s" % stack.name)
            if stack.exists_in_cf(self.cf_desc_stacks):
                self.logger.info("Stack %s already exists in cloudformation, skipping" % stack.name)
            else:
                if stack.deps_met(self.cf_desc_stacks) is False:
                    self.logger.critical("Dependancies for stack %s not met and they should be, exiting..." % stack.name)
                    exit(1)
                if not stack.populate_params(self.cf_desc_stacks):
                    self.logger.critical("Could not determine correct parameters for stack %s" % stack.name)
                    exit(1)

                stack.read_template()
                self.logger.info("Creating: %s, %s" % (stack.cf_stack_name, stack.get_params_tuples()))
                try:
                    self.cfconn.create_stack(
                        stack_name=stack.cf_stack_name,
                        template_body=stack.template_body,
                        parameters=stack.get_params_tuples(),
                        capabilities=['CAPABILITY_IAM'],
                        notification_arns=stack.sns_topic_arn,
                        tags=stack.tags
                    )
                except Exception as e:
                    self.logger.critical("Creating stack %s failed. Error: %s" % (stack.cf_stack_name, e))
                    exit(1)

                create_result = self.watch_events(stack.cf_stack_name, "CREATE_IN_PROGRESS")
                if create_result != "CREATE_COMPLETE":
                    self.logger.critical("Stack didn't create correctly, status is now %s" % create_result)
                    exit(1)

                #CF told us stack completed ok. Log message to that effect and refresh the list of stack objects in CF
                self.logger.info("Finished creating stack: %s" % stack.cf_stack_name)
                self.cf_desc_stacks = self.cfconn.describe_stacks()

    def delete(self, stack_name = None):
        """
        Delete all the stacks from cloudformation.
        Does this in reverse dependency order. Prompts for confirmation before deleting each stack
        """
        #Removing stacks so need to do it in reverse dependancy order
        for stack in reversed(self.stack_objs):
            if stack_name and stack.name != stack_name:
                continue
            self.logger.info("Starting checks for deletion of stack: %s" % stack.name)
            if not stack.exists_in_cf(self.cf_desc_stacks):
                self.logger.info("Stack %s doesn't exist in cloudformation, skipping" % stack.name)
            else:
                confirm = raw_input("Confirm you wish to delete stack %s (Name in CF: %s) (type 'yes' if so): " % (stack.name, stack.cf_stack_name))
                if not confirm == "yes":
                    print "Not confirmed, skipping..."
                    continue
                self.logger.info("Starting delete of stack %s" % stack.name)
                self.cfconn.delete_stack(stack.cf_stack_name)
                delete_result = self.watch_events(stack.cf_stack_name, "DELETE_IN_PROGRESS")
                if delete_result != "DELETE_COMPLETE" and delete_result != "STACK_GONE":
                    self.logger.critical("Stack didn't delete correctly, status is now %s" % delete_result)
                    exit(1)

                #CF told us stack completed ok. Log message to that effect and refresh the list of stack objects in CF
                self.logger.info("Finished deleting stack: %s" % stack.cf_stack_name)
                self.cf_desc_stacks = self.cfconn.describe_stacks()

    def update(self, stack_name = None):
        """
        Attempts to update each of the stacks if template or parameters are diffenet to whats currently in cloudformation
        If a stack doesn't already exist. Logs critical error and exits.
        """
        for stack in self.stack_objs:
            if stack_name and stack.name != stack_name:
                continue
            self.logger.info("Starting checks for update of stack: %s" % stack.name)
            if not stack.exists_in_cf(self.cf_desc_stacks):
                self.logger.critical("Stack %s doesn't exist in cloudformation, can't update something that doesn't exist." % stack.name)
                exit(1)
            if not stack.deps_met(self.cf_desc_stacks):
                self.logger.critical("Dependancies for stack %s not met and they should be, exiting..." % stack.name)
                exit(1)
            if not stack.populate_params(self.cf_desc_stacks):
                self.logger.critical("Could not determine correct parameters for stack %s" % stack.name)
                exit(1)
            stack.read_template()
            template_up_to_date = stack.template_uptodate(self.cf_desc_stacks)
            params_up_to_date = stack.params_uptodate(self.cf_desc_stacks)
            self.logger.debug("Stack is up to date: %s" % (template_up_to_date and params_up_to_date))
            if template_up_to_date and params_up_to_date:
                self.logger.info("Stack %s is already up to date with cloudformation, skipping..." % stack.name)
            else:
                if not template_up_to_date:
                    self.logger.info("Template for stack %s has changed." % stack.name)
                    #Would like to get this working. Tried datadiff at the moment but can't stop it from printing whole template
                    #stack.print_template_diff(self.cf_desc_stacks)
                self.logger.info("Starting update of stack %s with parameters: %s" % (stack.name, stack.get_params_tuples()))
                self.cfconn.validate_template(template_body = stack.template_body)
                    
                try:
                    self.cfconn.update_stack(
                            stack_name    = stack.cf_stack_name,
                            template_body = stack.template_body,
                            parameters    = stack.get_params_tuples(),
                            capabilities  = ['CAPABILITY_IAM'],
                            tags          = stack.tags
                            )
                except boto.exception.BotoServerError as e:
                    try:
                        e_message_dict = simplejson.loads(e.error_message)
                        if str(e_message_dict["Error"]["Message"]) == "No updates are to be performed.":
                            self.logger.error("Cloudformation has no updates to perform on %s, this might be because there is a parameter with NoEcho set" % stack.name)
                            continue
                        else:
                            self.logger.error("Got error message: %s" % e_message_dict["Error"]["Message"])
                            raise e
                    except simplejson.decoder.JSONDecodeError:
                        self.logger.critical("Unknown error updating stack: %s", e)
                        exit(1)
                update_result = self.watch_events(stack.cf_stack_name, ["UPDATE_IN_PROGRESS", "UPDATE_COMPLETE_CLEANUP_IN_PROGRESS"])
                if update_result != "UPDATE_COMPLETE":
                    self.logger.critical("Stack didn't update correctly, status is now %s" % update_result)
                    exit(1)

                self.logger.info("Finished updating stack: %s" % stack.cf_stack_name)

            #avoid getting rate limited
            time.sleep(2)

    def watch(self, stack_name):
        """
        Watch events for a given cloudformation stack. It will keep watching until its state changes
        """
        if not stack_name:
            self.logger.critical("No stack name passed in, nothing to watch... use -s to provide stack name.")
            exit(1)
        the_stack = False
        for stack in self.stack_objs:
            if stack_name == stack.name:
                the_stack = stack
        if not the_stack:
            self.logger.error("Cannot find stack %s to watch" % stack_name)
            return False
        the_cf_stack = the_stack.exists_in_cf(self.cf_desc_stacks)
        if not the_cf_stack:
            self.logger.error("Stack %s doesn't exist in cloudformation, can't watch something that doesn't exist." % stack.name)
            return False

        self.logger.info("Watching stack %s, while in state %s." % (the_stack.cf_stack_name, str(the_cf_stack.stack_status)))
        self.watch_events(the_stack.cf_stack_name, str(the_cf_stack.stack_status))


    def watch_events(self, stack_name, while_status):
        """
        Used by the various actions to watch cloudformation events while a stacks in a given state
        """
        try:
            cfstack_obj = self.cfconn.describe_stacks(stack_name)[0]
            events = list(self.cfconn.describe_stack_events(stack_name))
        except boto.exception.BotoServerError as e:
            if str(e.error_message) == "Stack:%s does not exist" % (stack_name):
                return "STACK_GONE"
        #print the last 5 events, so we get to see the start of the action we are performing
        self.logger.info("Last 5 events for this stack:")
        for e in reversed(events[:5]):
            self.logger.info("%s %s %s %s %s %s" % (e.timestamp.isoformat(), e.resource_status, e.resource_type, e.logical_resource_id, e.physical_resource_id, e.resource_status_reason))
        status = str(cfstack_obj.stack_status)
        self.logger.info("New events:")
        while status in while_status:
            try:
                new_events = list(self.cfconn.describe_stack_events(stack_name))
            except boto.exception.BotoServerError as e:
                if str(e.error_message) == "Stack:%s does not exist" % (stack_name):
                    return "STACK_GONE"
            x = 0
            events_to_log = []
            while events[0].timestamp != new_events[x].timestamp or events[0].logical_resource_id != new_events[x].logical_resource_id:
                events_to_log.insert(0, new_events[x])
                x += 1
            for event in events_to_log:
                self.logger.info("%s %s %s %s %s %s" % (event.timestamp.isoformat(), event.resource_status, event.resource_type, event.logical_resource_id, event.physical_resource_id, event.resource_status_reason))
            if x > 0:
                events = new_events[:]
            cfstack_obj.update()
            status = str(cfstack_obj.stack_status)
            time.sleep(5)
        return status



########NEW FILE########
